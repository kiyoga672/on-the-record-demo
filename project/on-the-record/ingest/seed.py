"""Import complete source sitting days, newest first, with auditable coverage."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, bulk, request
from ingest.xml_source import XMLSource


def run(days=1, since='2025-01-01'):
    source = XMLSource()
    source.load_identities()
    manifest_path = ROOT / '.local/coverage.json'
    manifest_path.parent.mkdir(exist_ok=True)
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'since': since, 'complete': False, 'days': {}}
    for house in ('representatives', 'senate'):
        available = [d for d in source.dates(house) if d >= since]
        selected = available[:days] if days else available
        for day in selected:
            docs, report = source.day(day, house)
            count = 0
            for offset in range(0, len(docs), 100):
                count += bulk('hansard', docs[offset:offset + 100], 'speech_id')
            report['indexed'] = count
            report['status'] = 'indexed' if count == len(docs) and not report['quarantined'] else 'partial'
            manifest['days'][f'{house}:{day}'] = report
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            print(f'{house} {day}: indexed={count}, quarantined={report["quarantined"]}', flush=True)
        manifest[f'{house}_available_days'] = available
    manifest['complete'] = all(
        manifest['days'].get(f'{house}:{day}', {}).get('status') == 'indexed'
        for house in ('representatives', 'senate') for day in manifest.get(f'{house}_available_days', []))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    request('es', 'POST', '/hansard/_refresh')
    print(f'Seed finished. Complete coverage: {manifest["complete"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=1, help='Complete sitting days per house; 0 = all available')
    args = parser.parse_args()
    run(args.days)
