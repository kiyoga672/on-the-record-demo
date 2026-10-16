"""Read-only capability and source checks; reports metadata without secrets or private rows."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, request, required
from ingest.oa_client import OpenAustralia, speech


def run():
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'checks': {}}

    def check(name, action):
        try:
            result = action()
            report['checks'][name] = {'ok': True, 'result': result}
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            report['checks'][name] = {'ok': False, 'error': str(exc)}
        print(name + ': ' + json.dumps(report['checks'][name], ensure_ascii=True), flush=True)

    api = OpenAustralia()
    representatives = []

    def source():
        required('OPENAUSTRALIA_KEY')
        rows = api.get('getRepresentatives')
        if not isinstance(rows, list) or not rows:
            raise RuntimeError('Expected a nonempty member list')
        representatives.extend(rows)
        return {'count': len(rows), 'fields': sorted(rows[0].keys())}

    def debates():
        if not representatives:
            raise RuntimeError('Member lookup must pass first')
        data = api.get('getDebates', type='representatives', person=representatives[0]['person_id'], num=1, page=1)
        rows = data.get('rows', [])
        result = {'row_count': len(rows), 'top_level_fields': sorted(data.keys())}
        if rows:
            row = rows[0]
            doc = speech(row, 'representatives')
            result.update({'row_fields': sorted(row.keys()), 'normalizer_passed': bool(doc),
                           'sample_date': row.get('hdate'), 'speaker_fields': sorted((row.get('speaker') or {}).keys())})
        return result

    def ml():
        data = request('es', 'GET', '/_nodes?filter_path=nodes.*.roles,nodes.*.attributes.ml.machine_memory')
        nodes = [v for v in data.get('nodes', {}).values() if 'ml' in v.get('roles', [])]
        return {'ml_node_count': len(nodes), 'memory_bytes': [n.get('attributes', {}).get('ml.machine_memory') for n in nodes],
                'autoscaling_verified': False}

    def inference():
        data = request('es', 'GET', '/_inference')
        return [{'id': e.get('inference_id'), 'task': e.get('task_type'), 'service': e.get('service'),
                 'model': e.get('service_settings', {}).get('model_id'),
                 'region': e.get('service_settings', {}).get('region')}
                for e in data.get('endpoints', [])]

    def connectors():
        data = request('kibana', 'GET', '/api/actions/connectors')
        rows = data if isinstance(data, list) else data.get('data', [])
        return [{'id': c.get('id'), 'type': c.get('connector_type_id'), 'name': c.get('name'),
                 'preconfigured': c.get('is_preconfigured'),
                 'inference_id': c.get('config', {}).get('inferenceId')}
                for c in rows]

    def privileges():
        result = request('es', 'POST', '/_security/user/_has_privileges', {
            'cluster': ['monitor', 'manage_inference'],
            'index': [{'names': ['hansard', 'members', 'watches', 'eval_runs'],
                       'privileges': ['create_index', 'read', 'write', 'view_index_metadata']}]})
        return {k: v for k, v in result.items() if k != 'username'}

    def schema():
        result = request('kibana', 'GET', '/api/workflows/schema?loose=true')
        (ROOT / '.local').mkdir(exist_ok=True)
        (ROOT / '.local/workflow-schema.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        return {'top_level_fields': sorted(result.keys()), 'saved': '.local/workflow-schema.json'}

    check('openaustralia_members', source)
    check('openaustralia_sample_speech', debates)
    check('ml_capacity', ml)
    check('inference_endpoints', inference)
    check('kibana_connectors', connectors)
    check('elasticsearch_privileges', privileges)
    check('workflow_schema', schema)
    (ROOT / '.local').mkdir(exist_ok=True)
    (ROOT / '.local/readiness.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    run()
