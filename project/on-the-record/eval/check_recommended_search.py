"""Live regression for a heading-only recommendation already present in the demo index."""
import argparse
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import request


def run(base):
    payload = {'speaker_id': '10954', 'speaker_name': 'Alex Antic', 'topic': 'Australian Society'}
    response = requests.post(base + '/api/timeline', json=payload, timeout=160)
    response.raise_for_status()
    result = response.json()
    assert result['status'] == 'verified', 'Recommended debate returned no verified quote'
    assert any(q['speech_id'] == 'senate:2026-10-13.178.2' for q in result['items'])
    for item in result['items']:
        hits = request('es', 'POST', '/hansard/_search', {'size': 1,
            'query': {'term': {'speech_id': item['speech_id']}}})['hits']['hits']
        assert hits and hits[0]['_source']['speaker_id'] == payload['speaker_id']
        assert item['quote'] in hits[0]['_source']['text']
    long_title = 'A New Tax System (Family Assistance) Amendment (No Jab No Pay Repeal) Bill 2025; Second Reading'
    response = requests.post(base + '/api/timeline', json={**payload, 'topic': long_title}, timeout=160)
    response.raise_for_status()
    bill = response.json()
    assert bill['status'] == 'verified' and any(q['speech_id'] == 'senate:2026-09-16.4.3' for q in bill['items']), 'Long bill-title recommendation failed verification'
    for item in bill['items']:
        source = request('es', 'POST', '/hansard/_search', {'size': 1,
            'query': {'term': {'speech_id': item['speech_id']}}})['hits']['hits'][0]['_source']
        assert source['speaker_id'] == payload['speaker_id'] and item['quote'] in source['text']
    response = requests.post(base + '/api/timeline', json={**payload, 'topic': 'quuxlorian teleportatorium'}, timeout=160)
    response.raise_for_status()
    negative = response.json()
    assert negative['items'] == [] and negative['status'] in ('incomplete_coverage', 'no_matches')
    response = requests.get(base + '/api/attention', params={'speaker_id': '10954', 'topic': payload['topic']}, timeout=90)
    response.raise_for_status()
    assert sum(row['n'] for row in response.json()['monthly']) >= 1
    print('PASS: both recommended titles return source-exact quotes; unknown topic stays empty; title-aware monthly count is present.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:3000')
    run(parser.parse_args().base_url.rstrip('/'))
