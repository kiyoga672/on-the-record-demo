"""Submit already normalized documents to the registered batch-ingestion Workflow."""
import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import required, request, ROOT


def run(documents, day):
    wid = required('DAILY_HANSARD_WORKFLOW_ID')
    result = request('kibana', 'POST', f'/api/workflows/workflow/{wid}/run', {'inputs': {'date': day, 'documents': documents}})
    eid = result['workflowExecutionId']
    print(f'Ingestion Workflow execution: {eid}', flush=True)
    for _ in range(60):
        state = request('kibana', 'GET', f'/api/workflows/executions/{eid}')
        if state['status'] == 'completed':
            return {'execution_id': eid, 'status': 'completed'}
        if state['status'] in ('failed', 'cancelled'):
            raise RuntimeError(f'Ingestion Workflow {state["status"]}; inspect execution {eid}')
        time.sleep(2)
    raise RuntimeError(f'Ingestion Workflow still running: {eid}')


if __name__ == '__main__':
    # Replay an existing source record without changing its identity or contents.
    data = request('es', 'POST', '/hansard/_search', {'size': 1, 'query': {'match_all': {}},
        '_source': ['speech_id', 'speaker_id', 'speaker_name', 'date', 'house', 'party', 'electorate', 'debate_title', 'text', 'url', 'word_count']})
    docs = [h['_source'] for h in data['hits']['hits']]
    if not docs:
        raise RuntimeError('No real indexed record available for replay')
    result = run(docs, docs[0]['date'][:10])
    (ROOT / '.local/ingestion-workflow-probe.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(result)
