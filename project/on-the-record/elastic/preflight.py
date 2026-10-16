"""Read-only deployment checks, plus explicit model warm-up. Prints no secrets."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ENV_PATH, ROOT, request, required
from dotenv import set_key


def run(warm=False):
    for name in ('ES_URL', 'KIBANA_URL', 'ES_API_KEY'):
        required(name)
    info = request('es', 'GET', '/')
    version = info['version']['number']
    parts = tuple(int(p) for p in version.split('-')[0].split('.')[:2])
    print(f'Elasticsearch version: {version}', flush=True)
    set_key(str(ENV_PATH), 'ES_VERSION', version)
    if parts < (9, 3):
        raise RuntimeError('Stack < 9.3: upgrade deployment before continuing')
    if parts < (9, 4):
        raise RuntimeError('9.3 is preview; this implementation requires 9.4+ supported APIs')
    endpoints = request('es', 'GET', '/_inference')
    ids = [p.get('inference_id') for p in endpoints.get('endpoints', [])]
    print(f'Inference endpoints: {", ".join(filter(None, ids))}', flush=True)
    missing = set(['.elser-2-elasticsearch', '.rerank-v1-elasticsearch']) - set(ids)
    tools = request('kibana', 'GET', '/api/agent_builder/tools')
    entries = tools if isinstance(tools, list) else tools.get('results', tools.get('tools', []))
    types = sorted({t.get('type', 'unknown') for t in entries})
    print(f'Agent Builder: {len(entries)} tools; existing types: {types}')
    print('Workflow tool creation support: not established by existing tool list; setup will validate registration')
    ml = request('es', 'GET', '/_ml/info')
    print(f'ML API reachable: {bool(ml)}. Verify node RAM >=4 GB and autoscaling in Cloud console.')
    if missing:
        raise RuntimeError(f'Required default inference endpoints missing: {sorted(missing)}')
    if warm:
        request('es', 'POST', '/_inference/sparse_embedding/.elser-2-elasticsearch', {'input': 'warm up'})
        print('ELSER warm-up: passed')
    report = {'version': version, 'inference_endpoints': ids, 'observed_tool_types': types,
              'elser_warmed': warm, 'ml_capacity_verified': False}
    (ROOT / '.local').mkdir(exist_ok=True)
    (ROOT / '.local/preflight.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--warm', action='store_true')
    args = parser.parse_args()
    try:
        run(args.warm)
    except RuntimeError as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        sys.exit(1)
