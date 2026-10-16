"""Deterministic, opt-in digest worker. Not scheduled or deployed by registration.

Dry-run is the default and emits counts only. A successful connector response precedes
state changes. An ambiguous failure leaves delivery_pending on the ownership marker,
blocking automatic retries until an operator reconciles delivery with the mail service.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys
from urllib.parse import quote as urlquote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ATTRIBUTION, request, required

SUBJECT = 'Your saved Hansard quotes'


def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=timezone.utc) if len(value) == 10 else datetime.fromisoformat(value.replace('Z', '+00:00'))


def due(doc, as_of, send_now=False):
    if not doc.get('quote_hash') or doc.get('record_kind') != 'quote':
        return False
    last = instant(doc['last_sent']) if doc.get('last_sent') else None
    if not doc.get('monthly'):
        return not doc.get('sent_at') and (send_now or instant(doc['remind_on']) <= as_of)
    # Initial reminder respects remind_on. Subsequent monthly reminders run on day 1;
    # explicit send-now can advance a pending month, but never resend within that month.
    if last and last.strftime('%Y-%m') >= as_of.strftime('%Y-%m'):
        return False
    return send_now or (instant(doc['remind_on']) <= as_of and (last is None or as_of.day == 1))


def message(documents):
    blocks = [SUBJECT]
    for doc in sorted(documents, key=lambda x: x['date'], reverse=True):
        day = instant(doc['date']).strftime('%d %b %Y')
        chamber = 'Senate' if doc['house'].lower() == 'senate' else 'House'
        blocks.append(f'{doc["speaker_name"]} ({doc["party"]}) on {doc["topic"]}\n"{doc["quote"]}"\n{day}, {chamber} — {doc["url"]}')
    blocks += [ATTRIBUTION, 'You received this because you saved these quotes on On the Record.']
    return '\n\n'.join(blocks)


def groups(hits, as_of, send_now=False):
    result = defaultdict(list)
    for hit in hits:
        if due(hit['_source'], as_of, send_now):
            result[hit['_source']['email']].append(hit)
    return result


def fetch_quotes(email=None):
    filters = [{'exists': {'field': 'quote_hash'}}, {'term': {'record_kind': 'quote'}}]
    if email:
        filters.append({'term': {'email': email}})
    after = None
    while True:
        body = {'size': 200, 'query': {'bool': {'filter': filters}}, 'sort': [{'quote_hash': 'asc'}, {'email': 'asc'}]}
        if after:
            body['search_after'] = after
        hits = request('es', 'POST', '/saved_quotes/_search', body)['hits']['hits']
        if not hits:
            break
        yield from hits
        after = hits[-1]['sort']


def deliver(hits, as_of, connector, transport=request, send_now=False):
    """At-most-one automatic attempt per outstanding group, including crash recovery."""
    email = hits[0]['_source']['email']
    owner = 'owner:' + hashlib.sha256(email.encode()).hexdigest()
    path = '/saved_quotes/_update/' + urlquote(owner, safe='')
    claimed = transport('es', 'POST', path, {'script': {'source':
        "if (ctx._source.delivery_pending == true) { ctx.op = 'noop'; } else { ctx._source.delivery_pending = true; }"}})
    if claimed.get('result') == 'noop':
        return False
    # Another worker may have sent the originally selected records before this claim.
    # Re-read after acquiring the shared durable ownership lock, never send stale hits.
    fresh = transport('es', 'POST', '/saved_quotes/_mget', {'ids': [h['_id'] for h in hits]})['docs']
    hits = [h for h in fresh if h.get('found') and h['_source'].get('email') == email and due(h['_source'], as_of, send_now)]
    if not hits:
        transport('es', 'POST', path, {'doc': {'delivery_pending': False}})
        return False
    # Never clear the claim on ambiguous send/update failure: blindly retrying could
    # duplicate a message. Reconciliation must inspect the provider before release.
    outcome = transport('kibana', 'POST', '/api/actions/connector/' + urlquote(connector, safe='') + '/_execute',
        {'params': {'to': [email], 'subject': SUBJECT, 'message': message([h['_source'] for h in hits])}})
    if outcome.get('status') != 'ok':
        raise RuntimeError('Connector did not confirm delivery; reconcile pending claim before retrying.')
    stamp = as_of.isoformat().replace('+00:00', 'Z')
    for hit in hits:
        fields = {'last_sent': stamp, 'sent_at': None if hit['_source'].get('monthly') else stamp}
        transport('es', 'POST', '/saved_quotes/_update/' + urlquote(hit['_id'], safe=''),
                  {'doc': fields, 'refresh': 'wait_for'})
    transport('es', 'POST', path, {'doc': {'delivery_pending': False}})
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', default=datetime.now(timezone.utc).isoformat())
    parser.add_argument('--email', help='Explicitly scope a manual delivery; never printed.')
    parser.add_argument('--send-now', action='store_true', help='All pending quotes for the explicitly selected email, regardless of reminder date.')
    parser.add_argument('--send', action='store_true', help='Actually execute the configured email connector. Default is dry-run.')
    args = parser.parse_args()
    if args.send_now and not args.email:
        parser.error('--send-now requires --email')
    as_of = instant(args.as_of)
    if as_of.tzinfo is None:
        parser.error('--as-of requires a timezone')
    pending = groups(fetch_quotes(args.email), as_of, args.send_now)
    count = sum(map(len, pending.values()))
    if not args.send:
        print(f'Dry-run: {len(pending)} recipient groups, {count} pending quotes; no email sent.')
        return
    connector = required('EMAIL_CONNECTOR_ID')
    sent = sum(deliver(hits, as_of, connector, send_now=args.send_now) for hits in pending.values())
    print(f'Confirmed {sent} digest deliveries; {len(pending) - sent} pending claims require reconciliation.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Service responses can echo recipient or body: never print them here.
        print(f'Digest worker failed ({type(exc).__name__}); no recipient/body details logged.', file=sys.stderr)
        sys.exit(1)
