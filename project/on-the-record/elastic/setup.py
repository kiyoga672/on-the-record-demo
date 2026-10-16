"""Idempotent project setup. Does not replace mappings or delete existing resources."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, request
from elastic.resources import MAPPINGS, tools, export


def upsert(kind, payload):
    path = f'/api/agent_builder/{kind}'
    current = request('kibana', 'GET', f'{path}/{payload["id"]}', allow=(404,))
    if current is None:
        request('kibana', 'POST', path, payload)
    else:
        allowed = ('description', 'configuration', 'tags') if kind == 'tools' else ('name', 'description', 'configuration', 'avatar_color', 'avatar_symbol')
        request('kibana', 'PUT', f'{path}/{payload["id"]}', {k: v for k, v in payload.items() if k in allowed})
    print(f'{kind}: {payload["id"]} ready', flush=True)


def run():
    export()
    for index, mapping in MAPPINGS.items():
        exists = request('es', 'HEAD', f'/{index}', allow=(404,))
        if exists is None:
            request('es', 'PUT', f'/{index}', mapping)
        print(f'Index {index}: ready', flush=True)
    for tool in tools():
        upsert('tools', tool)
    ids = [t['id'] for t in tools()]
    existing_agent = request('kibana', 'GET', '/api/agent_builder/agents/' + os.getenv('AGENT_ID', 'on-the-record'), allow=(404,))
    if existing_agent:
        ids = sorted(set(ids + [tool_id for group in existing_agent.get('configuration', {}).get('tools', []) for tool_id in group.get('tool_ids', [])]))
    agent = {'id': os.getenv('AGENT_ID', 'on-the-record'), 'name': 'On the Record',
             'description': 'Verbatim, source-verified Australian parliamentary statements.',
             'avatar_color': '#123C4A', 'avatar_symbol': 'OR',
             'configuration': {'instructions': (ROOT / 'elastic/agent/instructions.md').read_text(encoding='utf-8'),
                               'tools': [{'tool_ids': ids}]}}
    (ROOT / 'elastic/agent/on_the_record.json').write_text(json.dumps(agent, indent=2), encoding='utf-8')
    upsert('agents', agent)
    if os.getenv('BEDROCK_INFERENCE_ID'):
        from elastic.workflows.register import run as register_workflows
        register_workflows()


if __name__ == '__main__':
    run()
