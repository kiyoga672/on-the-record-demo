"""Native, deterministic digest plan. Disabled until connector delivery is verified."""
import os
from copy import deepcopy


def definition():
    as_of = "{{ inputs.as_of | default: execution.startedAt | date: '%Y-%m-%dT%H:%M:%SZ' }}"
    connector = os.getenv('EMAIL_CONNECTOR_ID') or 'EMAIL_CONNECTOR_NOT_CONFIGURED'
    pending_script = """def s = params._source;
if (s.record_kind != 'quote' || s.quote_hash == null) { emit(false); return; }
boolean now = params.send_now == true || params.send_now == 'true';
String today = params.as_of.substring(0, 10);
String month = today.substring(0, 7);
boolean initial = s.last_sent == null;
boolean sameMonth = !initial && s.last_sent.substring(0,7).compareTo(month) >= 0;
boolean dateDue = s.remind_on.substring(0,10).compareTo(today) <= 0;
if (s.monthly == true) { emit(!sameMonth && (now || (dateDue && (initial || today.substring(8,10) == '01')))); }
else { emit(s.sent_at == null && (now || dateDue)); }
"""
    body = """Your saved Hansard quotes

{% for hit in foreach.item.quotes.hits.hits %}{{ hit._source.speaker_name }} ({{ hit._source.party }}) on {{ hit._source.topic }}
"{{ hit._source.quote }}"
{{ hit._source.date | date: '%d %b %Y' }}, {% assign chamber = hit._source.house | downcase %}{% if chamber == 'senate' %}Senate{% else %}House{% endif %} — {{ hit._source.url }}

{% endfor %}Source: Parliament of Australia Hansard via OpenAustralia.
You received this because you saved these quotes on On the Record."""
    workflow = {'version': '1', 'name': 'reminder_digest',
        'description': 'Native deterministic saved-quote reminders. Disabled pending EMAIL_CONNECTOR_ID configuration and authorized delivery verification. No LLM. Ambiguous delivery leaves an ownership claim requiring reconciliation.',
        'enabled': False, 'settings': {'timezone': 'UTC', 'concurrency': {'key': 'saved-quote-digest', 'strategy': 'queue', 'max': 1}},
        'triggers': [{'type': 'scheduled', 'with': {'every': '1d'}}, {'type': 'manual', 'inputs': {
            'type': 'object', 'properties': {'as_of': {'type': 'string'}, 'email': {'type': 'string'},
                'management_hash': {'type': 'string'}, 'send_now': {'type': 'boolean', 'default': False}}, 'additionalProperties': False}}],
        'steps': [
            {'name': 'find_pending', 'type': 'elasticsearch.request', 'with': {'method': 'POST', 'path': '/saved_quotes/_search', 'body': {
                'size': 0, 'runtime_mappings': {'digest_due': {'type': 'boolean', 'script': {'source': pending_script,
                    'params': {'as_of': as_of, 'send_now': '{{ inputs.send_now | default: false }}'}}}},
                'query': {'bool': {'filter': [{'term': {'digest_due': True}}, {'exists': {'field': 'quote_hash'}},
                    {'script': {'script': {'source': "if (params.send_now == true || params.send_now == 'true') { return params.email != '' && doc['email'].value == params.email; } return params.email == '' || doc['email'].value == params.email;",
                        'params': {'email': "{{ inputs.email | default: '' }}", 'send_now': '{{ inputs.send_now | default: false }}'}}}}]}},
                'aggs': {'recipients': {'terms': {'field': 'email', 'size': 1000}}}}}},
            {'name': 'recipient_groups', 'type': 'foreach', 'foreach': '{{ steps.find_pending.output.aggregations.recipients.buckets }}', 'steps': [
                {'name': 'lookup_owner', 'type': 'elasticsearch.search', 'with': {'index': 'saved_quotes', 'size': 1, 'query': {'bool': {'filter': [
                    {'term': {'record_kind': 'ownership'}}, {'term': {'email': '{{ foreach.item.key }}'}}]}}}},
                {'name': 'claim_delivery', 'type': 'elasticsearch.request', 'if': 'steps.lookup_owner.output.hits.total.value : 1', 'with': {
                    'method': 'POST', 'path': '/saved_quotes/_update/{{ steps.lookup_owner.output.hits.hits[0]._id }}', 'body': {
                        'script': {'source': "boolean now = params.send_now == true || params.send_now == 'true'; if (ctx._source.delivery_pending == true || (now && ctx._source.management_hash != params.management_hash)) { ctx.op = 'noop'; } else { ctx._source.delivery_pending = true; }",
                            'params': {'send_now': '{{ inputs.send_now | default: false }}', 'management_hash': "{{ inputs.management_hash | default: '' }}"}}}}},
                {'name': 'send_digest', 'type': 'kibana.request', 'if': 'steps.claim_delivery.output.result : "updated"', 'with': {
                    'method': 'POST', 'path': '/api/actions/connector/' + connector + '/_execute',
                    'body': {'params': {'to': ['{{ foreach.item.key }}'], 'subject': 'Your saved Hansard quotes', 'message': body}}}},
                {'name': 'mark_sent', 'type': 'elasticsearch.request', 'if': 'steps.send_digest.output.status : "ok"',
                    'foreach': '{{ foreach.item.quotes.hits.hits }}', 'with': {'method': 'POST', 'path': '/saved_quotes/_update/{{ foreach.item._id }}',
                        'body': {'script': {'source': "ctx._source.last_sent = params.stamp; ctx._source.sent_at = ctx._source.monthly == true ? null : params.stamp;", 'params': {'stamp': as_of}}}, 'params': {'refresh': 'wait_for'}}},
                {'name': 'release_delivery', 'type': 'elasticsearch.request', 'if': 'steps.send_digest.output.status : "ok"', 'with': {
                    'method': 'POST', 'path': '/saved_quotes/_update/{{ steps.lookup_owner.output.hits.hits[0]._id }}',
                    'body': {'doc': {'delivery_pending': False}}}}
            ]},
            {'name': 'completed', 'type': 'console', 'with': {'message': 'Digest run completed; inspect statuses for delivery confirmation. No recipient or message details are logged by this console step.'}}
        ]}
    # Re-read under the durable email lock: a concurrently started manual/scheduled
    # worker can otherwise act on a stale selection after another delivery releases it.
    refresh = deepcopy(workflow['steps'][0]['with']['body'])
    refresh.pop('aggs')
    refresh.update(size=1000, sort=[{'date': 'desc'}])
    refresh['query']['bool']['filter'].append({'term': {'email': '{{ foreach.item.key }}'}})
    steps = workflow['steps'][1]['steps']
    steps.insert(2, {'name': 'refresh_pending', 'type': 'elasticsearch.request', 'if': 'steps.claim_delivery.output.result : "updated"',
        'with': {'method': 'POST', 'path': '/saved_quotes/_search', 'body': refresh}})
    steps[3]['if'] = 'steps.claim_delivery.output.result : "updated" and steps.refresh_pending.output.hits.total.value > 0'
    steps[3]['with']['body']['params']['message'] = body.replace('foreach.item.quotes.hits.hits', 'steps.refresh_pending.output.hits.hits')
    steps[4]['foreach'] = '{{ steps.refresh_pending.output.hits.hits }}'
    steps[5]['if'] = 'steps.claim_delivery.output.result : "updated" and (steps.refresh_pending.output.hits.total.value : 0 or steps.send_digest.output.status : "ok")'
    return workflow
