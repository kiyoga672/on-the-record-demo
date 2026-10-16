"""Evaluate delivered quotes against fresh source, record failure instead of inventing success."""
import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, bulk, request


def run(url, limit, expected=None):
    cases = json.loads((ROOT / 'eval/golden.json').read_text())
    if expected:
        cases = [c for c in cases if c['expected'] == expected]
    run_id = str(uuid.uuid4())
    records = []
    for i, case in enumerate(cases[:limit] if limit else cases):
        start = time.monotonic()
        answer = None
        http_status = None
        failure_reason = None
        try:
            response = requests.post(url + '/api/timeline', json={k: case[k] for k in ('speaker_id', 'speaker_name', 'topic')}, timeout=400)
            http_status = response.status_code
            if not response.ok:
                failure_reason = response.json().get('error', 'Request failed')
            response.raise_for_status()
            answer = response.json()
        except requests.RequestException:
            pass
        items = answer.get('items', []) if answer else []
        verified = 0
        for item in items:
            data = request('es', 'POST', '/hansard/_search', {'size': 1, 'query': {'term': {'speech_id': item['speech_id']}}})
            hits = data['hits']['hits']
            if hits:
                source = hits[0]['_source']
                verified += int(source['speaker_id'] == case['speaker_id'] and item['quote'] in source['text']
                    and 0 < len(item['quote'].split()) <= 60 and item['date'] == source['date'] and item['url'] == source['url'])
        record = {'run_id': run_id, 'timestamp': datetime.now(timezone.utc).isoformat(),
          'question': case['question'], 'expected': case['expected'], 'quotes_total': len(items),
          'quotes_verified': verified, 'latency_ms': int((time.monotonic() - start) * 1000),
          'case_id': f'{run_id}:{i}', 'scope': case.get('scope'),
          'service_ok': answer is not None, 'answer_correct': bool(items) and verified == len(items) if case['expected'] == 'answerable' else None,
          'http_status': http_status, 'failure_reason': failure_reason,
          'result_status': answer.get('status') if answer else 'unavailable', 'judge_status': 'not_run'}
        if case['expected'] == 'unanswerable':
            if answer and answer.get('coverage', {}).get('complete'):
                expected = f'No recorded statements by {case["speaker_name"]} on {case["topic"]} in Hansard since 1 Jan 2025.'
                record['refusal_correct'] = expected == answer.get('message') and not items
            else:
                record['refusal_scope_status'] = 'not_evaluable_full_hansard_coverage_incomplete'
                record['indexed_scope_refusal_correct'] = bool(answer and not items and answer.get('status') == 'incomplete_coverage')
        records.append(record)
        bulk('eval_runs', [record], 'case_id')
        print(f'Case {i+1}: status={record["result_status"]}, verified={verified}/{len(items)}', flush=True)
    request('es', 'POST', '/eval_runs/_refresh')
    (ROOT / '.local/eval-latest.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(f'Evaluation run {run_id}; judge not run; zero-quote answers do not count as grounded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:3000')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--expected', choices=['answerable', 'unanswerable'])
    args = parser.parse_args()
    run(args.url, args.limit, args.expected)
