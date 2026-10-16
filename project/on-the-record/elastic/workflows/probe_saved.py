"""Explicit isolated save probe, no mail, cleans only newly created probe IDs."""
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import request


def run():
    speech = request('es', 'POST', '/hansard/_search', {'size': 1, 'query': {'bool': {'filter': [{'exists': {'field': 'speaker_name'}}, {'exists': {'field': 'party'}}]}}})['hits']['hits'][0]['_source']
    email = 'probe-' + uuid.uuid4().hex + '@example.invalid'
    owner = 'owner:' + hashlib.sha256(email.encode()).hexdigest()
    management = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    quote = ' '.join(speech['text'].split(' ')[:10])
    qhash = hashlib.sha256((speech['speaker_id'] + quote).encode()).hexdigest()
    did = hashlib.sha256((email + qhash).encode()).hexdigest()
    inputs = {k: speech[k] for k in ['speech_id', 'speaker_id', 'speaker_name', 'party', 'date', 'house', 'url']}
    inputs.update(email=email, quote=quote, quote_hash=qhash, document_id=did, management_hash=management,
                  topic='probe', remind_on='2027-01-01', monthly=False)
    execution_ids = []
    try:
        request('es', 'PUT', '/saved_quotes/_create/' + owner + '?refresh=wait_for', {'email': email, 'management_hash': management, 'record_kind': 'ownership'})
        for number in range(2):
            execution = request('kibana', 'POST', '/api/workflows/workflow/otr-save-quote/run', {'inputs': inputs})
            eid = execution.get('workflowExecutionId') or execution.get('id')
            execution_ids.append(eid)
            for _ in range(60):
                result = request('kibana', 'GET', '/api/workflows/executions/' + eid)
                if result.get('status') not in ('pending', 'running', 'queued'):
                    break
                time.sleep(1)
            print('Run', number + 1, 'status', result.get('status'))
            for step in result.get('stepExecutions', []):
                if step.get('status') == 'failed':
                    # source/query includes synthetic personal data only; don't print it.
                    print('Failed step:', step.get('stepId'), 'error:', json.dumps(step.get('error'))[:1500])
            stored = request('es', 'GET', '/saved_quotes/_doc/' + did, allow=(404,))
            print('Stored:', stored is not None)
            if not stored:
                for step in result.get('stepExecutions', []):
                    detail = request('kibana', 'GET', '/api/workflows/executions/' + eid + '/step/' + step['id'])
                    output = detail.get('output')
                    print('Step', step.get('stepId'), 'status', step.get('status'), 'output keys:', list(output) if isinstance(output, dict) else type(output).__name__)
                raise RuntimeError('Workflow did not create source-verified probe')
        print('Two saves keep one ID, source-exact quote stored:', stored['_source']['quote'] == quote)
        print('Execution IDs:', ', '.join(execution_ids))
    finally:
        for docid in [did, owner]:
            request('es', 'DELETE', '/saved_quotes/_doc/' + docid + '?refresh=wait_for', allow=(404,))


if __name__ == '__main__':
    run()
