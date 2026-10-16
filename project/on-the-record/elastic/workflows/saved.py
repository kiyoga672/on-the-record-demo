"""Saved-quote definitions. Digest stays disabled until its worker is deployed."""
import json
import os
from pathlib import Path
import sys
import yaml
from dotenv import set_key

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ROOT, ENV_PATH, request


def definitions():
    strings = ['document_id', 'email', 'speaker_id', 'speaker_name', 'party', 'topic', 'quote', 'date',
               'house', 'url', 'remind_on', 'quote_hash', 'management_hash', 'speech_id']
    props = {k: {'type': 'string'} for k in strings}
    props['monthly'] = {'type': 'boolean'}
    doc = {k: '{{ inputs.' + k + ' }}' for k in strings if k != 'document_id'}
    doc.update(monthly='{{ inputs.monthly }}', record_kind='quote', created_at="{{ execution.startedAt | date: '%Y-%m-%dT%H:%M:%SZ' }}", sent_at=None, last_sent=None)
    doc['speaker_name'] = '{{ foreach.item._source.speaker_name }}'
    doc['party'] = '{{ foreach.item._source.party }}'
    # A Workflow tool can be called independently of the application API. Repeat source and
    # ownership checks here; the application additionally performs its verify_quote tool call.
    source_query = {'bool': {'filter': [
        {'term': {k: '{{ inputs.' + k + ' }}'}} for k in ['speech_id', 'speaker_id', 'url', 'house']
    ] + [{'range': {'date': {'gte': '2025-01-01'}}}, {'term': {'source_exact': True}}]}}
    save = {'version': '1', 'name': 'save_quote', 'description': 'Save an explicitly requested source-exact quote after capability ownership verification. Existing saves are unchanged.',
        'enabled': True, 'triggers': [{'type': 'manual', 'inputs': {'type': 'object', 'properties': props,
            'required': list(props), 'additionalProperties': False}}], 'steps': [
        {'name': 'check_owner', 'type': 'elasticsearch.search', 'with': {'index': 'saved_quotes', 'size': 1,
            'query': {'bool': {'filter': [{'term': {'record_kind': 'ownership'}}, {'term': {'email': '{{ inputs.email }}'}},
                {'term': {'management_hash': '{{ inputs.management_hash }}'}}]}}}},
        {'name': 'verify_source', 'type': 'elasticsearch.request', 'if': 'steps.check_owner.output.hits.total.value : 1', 'with': {
            'method': 'POST', 'path': '/hansard/_search', 'body': {'size': 1, '_source': ['speaker_name', 'party'],
            'runtime_mappings': {'source_exact': {'type': 'boolean', 'script': {
                'source': "String q = params.quote; emit(q.length() > 0 && q.trim().splitOnToken(' ').length <= 60 && params._source.text.contains(q) && params._source.date.substring(0,10) == params.date.substring(0,10));",
                'params': {'quote': '{{ inputs.quote }}', 'date': '{{ inputs.date }}'}}}},
            'query': source_query}}},
        {'name': 'save_verified', 'type': 'elasticsearch.update', 'foreach': '{{ steps.verify_source.output.hits.hits }}',
            'with': {'index': 'saved_quotes', 'id': '{{ inputs.document_id }}', 'refresh': 'wait_for',
                'script': {'source': "ctx.op = 'noop';"}, 'upsert': doc}},
        {'name': 'confirmation', 'type': 'console', 'with': {'message': 'Save processing completed. Application must confirm document exists before reporting success.'}}]}
    from elastic.workflows.reminder_definition import definition
    digest = definition()
    return {'save_quote': save, 'reminder_digest': digest}


def register():
    from elastic.resources import MAPPINGS
    from elastic.setup import upsert
    if request('es', 'HEAD', '/saved_quotes', allow=(404,)) is None:
        request('es', 'PUT', '/saved_quotes', MAPPINGS['saved_quotes'])
    for name, definition in definitions().items():
        source = yaml.safe_dump(definition, sort_keys=False, allow_unicode=True)
        (ROOT / 'elastic/workflows' / f'{name}.yaml').write_text(source, encoding='utf-8')
        wid = 'otr-' + name.replace('_', '-')
        exists = request('kibana', 'GET', '/api/workflows/workflow/' + wid, allow=(404,))
        result = request('kibana', 'PUT' if exists else 'POST', '/api/workflows/workflow/' + wid if exists else '/api/workflows/workflow',
                         {'yaml': source} if exists else {'id': wid, 'yaml': source})
        if result.get('valid') is False or result.get('validationErrors'):
            raise RuntimeError(f'{name} workflow validation failed: ' + json.dumps(result.get('validationErrors')))
        key = name.upper() + '_WORKFLOW_ID'
        if os.getenv(key) != wid:
            set_key(str(ENV_PATH), key, wid)
        print(f'{wid}: valid, enabled={definition["enabled"]}')
    tool = {'id': 'save_quote', 'type': 'workflow', 'description': 'Save a source-verified quote only on explicit user request. Requires server-issued document ID, hash and management capability hash; never invent these. The server must confirm storage after execution. No email is sent.',
        'configuration': {'workflow_id': 'otr-save-quote', 'wait_for_completion': True}}
    (ROOT / 'elastic/tools/save_quote.json').write_text(json.dumps(tool, indent=2), encoding='utf-8')
    upsert('tools', tool)
    agent = request('kibana', 'GET', '/api/agent_builder/agents/on-the-record')
    config = agent['configuration']
    config['tools'][0]['tool_ids'] = sorted(set(config['tools'][0]['tool_ids'] + ['save_quote']))
    request('kibana', 'PUT', '/api/agent_builder/agents/on-the-record', {'configuration': config})
    path = ROOT / 'elastic/agent/on_the_record.json'
    saved = json.loads(path.read_text(encoding='utf-8'))
    saved['configuration'] = config
    path.write_text(json.dumps(saved, indent=2), encoding='utf-8')


if __name__ == '__main__':
    register()
