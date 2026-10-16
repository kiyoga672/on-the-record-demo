import argparse
import sys
from pathlib import Path
from datetime import date, datetime, timezone
import json
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, bulk, request
from ingest.xml_source import XMLSource


def save_manifest(path, manifest):
    manifest['updated_at'] = datetime.now(timezone.utc).isoformat()
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    temp.replace(path)


def covered(report):
    return (report.get('status') in ('indexed', 'partial')
            and report.get('indexed') == report.get('parsed') and 'sha256' in report)


def run(since='2025-01-01', until=None, limit=6000, batch_size=20):
    until = until or date.today().isoformat()
    if date.fromisoformat(since) > date.fromisoformat(until):
        raise ValueError('since must not be after until')
    if limit < 1 or not 1 <= batch_size <= 100:
        raise ValueError('limit must be positive; batch-size must be 1..100')
    folder = ROOT / '.local'
    folder.mkdir(exist_ok=True)
    lock = folder / 'backfill.lock'
    handle = lock.open('x')
    try:
        handle.write(str(datetime.now(timezone.utc)))
        handle.close()
        source = XMLSource()
        source.load_identities()
        path = folder / 'coverage.json'
        manifest = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'days': {}}
        manifest['since'] = min(manifest.get('since', since), since)
        manifest['complete'] = False
        plan = []
        for house in ('representatives', 'senate'):
            available = [d for d in source.dates(house) if d >= manifest['since']]
            manifest[f'{house}_available_days'] = available
            plan.extend((d, house) for d in available if since <= d <= until)
        plan.sort(reverse=True)
        save_manifest(path, manifest)
        count = days = 0
        for day, house in plan:
            key = f'{house}:{day}'
            if covered(manifest['days'].get(key, {})):
                continue
            docs, report = source.day(day, house)
            if count + len(docs) > limit:
                print(f'Batch budget reached: {count}/{limit}; next complete day {key} has {len(docs)} documents.', flush=True)
                break
            report['indexed'] = 0
            report['status'] = 'indexing'
            manifest['days'][key] = report
            save_manifest(path, manifest)
            for offset in range(0, len(docs), batch_size):
                # Stable source IDs make retry after interruption idempotent.
                report['indexed'] += bulk('hansard', docs[offset:offset + batch_size], 'speech_id')
                save_manifest(path, manifest)
                time.sleep(.25)
            report['status'] = ('source_missing' if 'sha256' not in report else
                                'partial' if report['quarantined'] else 'indexed')
            save_manifest(path, manifest)
            count += len(docs)
            days += 1
            print(f'{key}: indexed={report["indexed"]}, quarantined={report["quarantined"]}; run={count}', flush=True)
        manifest['complete'] = all(
            manifest['days'].get(f'{h}:{d}', {}).get('status') == 'indexed'
            for h in ('representatives', 'senate') for d in manifest[f'{h}_available_days'])
        save_manifest(path, manifest)
        request('es', 'POST', '/hansard/_refresh')
        result = {'indexed_this_run': count, 'days_this_run': days,
                  'documents': request('es', 'GET', '/hansard/_count')['count'],
                  'complete': manifest['complete']}
        print(json.dumps(result), flush=True)
        return result
    finally:
        handle.close()
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--since', default='2025-01-01')
    parser.add_argument('--until', default=date.today().isoformat())
    parser.add_argument('--limit', type=int, default=6000)
    parser.add_argument('--batch-size', type=int, default=20)
    args = parser.parse_args()
    run(args.since, args.until, args.limit, args.batch_size)
