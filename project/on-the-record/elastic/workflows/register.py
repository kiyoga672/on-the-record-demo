"""Version-tested workflow definitions. Does not run workflows or send mail."""
import json
import os
import sys
from pathlib import Path
import yaml
from dotenv import set_key
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ROOT, ENV_PATH, request, required
from elastic.setup import upsert


def workflow(name, inputs, steps):
    return {'version': '1', 'name': name, 'description': f'On the Record: {name}',
            'enabled': True, 'triggers': [{'type': 'manual', 'inputs': [
                {'name': n, 'type': 'string', 'required': True} for n in inputs]}], 'steps': steps}


def run():
    definitions = {
      'find_my_mp': workflow('find_my_mp', ['speaker_id'], [
          {'name': 'lookup', 'type': 'elasticsearch.search', 'with': {'index': 'members', 'size': 1,
              'query': {'term': {'person_id': '{{ inputs.speaker_id }}'}}}}]),
      'follow_topic': workflow('follow_topic', ['watch_id', 'email', 'speaker_id', 'speaker_name', 'topic', 'created_at'], [
          {'name': 'save_watch', 'type': 'elasticsearch.index', 'with': {'index': 'watches',
              'id': '{{ inputs.watch_id }}', 'refresh': 'wait_for', 'document': {k: '{{ inputs.' + k + ' }}'
              for k in ['email', 'speaker_id', 'speaker_name', 'topic', 'created_at']}}},
          {'name': 'confirmation', 'type': 'console', 'with': {'message': 'Topic watch saved.'}}]),
      'export_factsheet': workflow('export_factsheet', ['speaker_id', 'speaker_name', 'topic', 'candidates'], [
          {'name': 'select_quotes', 'type': 'ai.agent', 'agent-id': 'on-the-record',
           'inference-id': required('BEDROCK_INFERENCE_ID'), 'with': {
             'configuration_overrides': {'tools': [], 'instructions': 'Prepare candidate verbatim excerpts from supplied Hansard records only. You do not verify or deliver them; the application MUST call verify_quote and fresh source validation before displaying or downloading any output. Select up to two relevant continuous quotations of at most 60 words. Never paraphrase or infer a position. Do not call tools. Return the requested JSON schema with exact speech_id and quote. Never claim these drafts are verified.'},
             'message': 'Return candidate items:[{speech_id,quote}] only. Select up to two relevant continuous excerpts from supplied hybrid candidates for speaker_id={{ inputs.speaker_id }} on topic={{ inputs.topic }}. Do not call tools. The app will run verify_quote and exact source checks before any delivery. Candidates: {{ inputs.candidates }}',
             'schema': {'type': 'object', 'properties': {'items': {'type': 'array', 'maxItems': 8,
               'items': {'type': 'object', 'properties': {'speech_id': {'type': 'string'}, 'quote': {'type': 'string'}},
                         'required': ['speech_id', 'quote'], 'additionalProperties': False}}}, 'required': ['items'], 'additionalProperties': False}}}])
    }
    daily = workflow('daily_hansard', [], [
        {'name': 'index_speeches', 'type': 'elasticsearch.index', 'foreach': '{{ inputs.documents }}',
         'with': {'index': 'hansard', 'id': '{{ foreach.item.speech_id }}', 'document': {
             k: '{{ foreach.item.' + k + ' }}' for k in ['speech_id', 'speaker_id', 'speaker_name', 'date', 'house', 'party', 'electorate', 'debate_title', 'text', 'url', 'word_count']}}},
        {'name': 'ingest_complete', 'type': 'console', 'with': {'message': 'Provided Hansard source batch indexed. Source date: {{ inputs.date }}'}}])
    daily['description'] = 'Index a source-validated batch supplied by the ingestion worker. Scheduling, watch matching and email are not configured.'
    daily['triggers'][0]['inputs'] = {'type': 'object', 'properties': {
        'date': {'type': 'string'}, 'documents': {'type': 'array', 'maxItems': 100, 'items': {'type': 'object',
          'properties': {k: {'type': 'string'} for k in ['speech_id', 'speaker_id', 'speaker_name', 'date', 'house', 'party', 'electorate', 'debate_title', 'text', 'url']},
          'required': ['speech_id', 'speaker_id', 'speaker_name', 'date', 'house', 'text', 'url'], 'additionalProperties': True}}},
          'required': ['date', 'documents'], 'additionalProperties': False}
    definitions['daily_hansard'] = daily
    ids = []
    for name, definition in definitions.items():
        source = yaml.safe_dump(definition, sort_keys=False, allow_unicode=True)
        (Path(__file__).parent / f'{name}.yaml').write_text(source, encoding='utf-8')
        wid = f'otr-{name.replace("_", "-")}'
        current = request('kibana', 'GET', f'/api/workflows/workflow/{wid}', allow=(404,))
        if current is None:
            result = request('kibana', 'POST', '/api/workflows/workflow', {'id': wid, 'yaml': source})
        else:
            result = request('kibana', 'PUT', f'/api/workflows/workflow/{wid}', {'yaml': source})
        # The API returns validation errors even on some successful HTTP responses.
        if result.get('validationErrors') or result.get('valid') is False:
            raise RuntimeError(f'Workflow {name} did not validate: {result.get("validationErrors") or "inspect GET workflow valid flag"}')
        env_name = name.upper() + '_WORKFLOW_ID'
        if os.getenv(env_name) != wid:
            set_key(str(ENV_PATH), env_name, wid)
        if name == 'daily_hansard':
            print(f'Workflow {wid}: registered (worker-triggered batch ingestion only)', flush=True)
            continue
        tool = {'id': name, 'type': 'workflow', 'description':
           ('Resolve a known person ID to a member record. This deployment has no verified postcode mapping.' if name == 'find_my_mp' else
            'Store a topic watch only after an explicit user request including email. No emails are sent by this action.' if name == 'follow_topic' else
            'Prepare quote candidates for an explicit fact sheet export request. Final source verification is mandatory before delivery.'),
                'configuration': {'workflow_id': wid, 'wait_for_completion': True}}
        (ROOT / 'elastic/tools' / f'{name}.json').write_text(json.dumps(tool, indent=2), encoding='utf-8')
        upsert('tools', tool)
        ids.append(name)
        print(f'Workflow {wid}: registered', flush=True)
    agent = request('kibana', 'GET', '/api/agent_builder/agents/on-the-record')
    config = agent['configuration']
    config['tools'][0]['tool_ids'] = sorted(set(config['tools'][0]['tool_ids'] + ids))
    request('kibana', 'PUT', '/api/agent_builder/agents/on-the-record', {'configuration': config})
    exported = ROOT / 'elastic/agent/on_the_record.json'
    saved = json.loads(exported.read_text(encoding='utf-8'))
    saved['configuration'] = config
    exported.write_text(json.dumps(saved, indent=2), encoding='utf-8')
    print('Agent workflow tools attached')
    from elastic.workflows.saved import register as register_saved
    register_saved()


if __name__ == '__main__':
    run()
