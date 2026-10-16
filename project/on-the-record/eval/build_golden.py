"""Construct provisional cases from real index hits. Never assert full-Hansard absence."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, request


def run():
    cases = []
    for topic in ['housing', 'health', 'energy', 'education', 'tax', 'transport', 'defence', 'climate', 'childcare', 'migration', 'employment', 'infrastructure', 'taxation']:
        if len(cases) >= 10:
            break
        result = request('es', 'POST', '/hansard/_search', {'size': 1, 'query': {'match': {'text': topic}},
            '_source': ['speaker_id', 'speaker_name', 'speech_id']})
        hits = result['hits']['hits']
        if hits:
            s = hits[0]['_source']
            cases.append({'question': f'What has {s["speaker_name"]} said about {topic}?',
              'speaker_id': s['speaker_id'], 'speaker_name': s['speaker_name'], 'topic': topic,
              'expected': 'answerable', 'evidence_speech_id': s['speech_id'], 'scope': 'indexed_material'})
    if cases:
        for topic in ['quuxlorian teleportatorium', 'zygomorphic unobtainium',
                      'unicorn antimatter pensions', 'neptunian submarine gardens', 'invisible dragon mortgages']:
            base = cases[0]
            r = request('es', 'POST', '/hansard/_count', {'query': {'bool': {'filter': [{'term': {'speaker_id': base['speaker_id']}}],
                'must': [{'match': {'text': {'query': topic, 'operator': 'or'}}}]}}})
            if r['count'] == 0:
                cases.append({'question': f'What has {base["speaker_name"]} said about {topic}?',
                  'speaker_id': base['speaker_id'], 'speaker_name': base['speaker_name'], 'topic': topic,
                  'expected': 'unanswerable', 'scope': 'indexed_material', 'global_absence_confirmed': False})
    path = ROOT / 'eval/golden.json'
    path.write_text(json.dumps(cases, indent=2), encoding='utf-8')
    print(f'Created {len(cases)} source-backed provisional cases; scope=indexed_material, not all Hansard')


if __name__ == '__main__':
    run()
