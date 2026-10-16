import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, bulk
from ingest.xml_source import XMLSource
from ingest.workflow_ingest import run as workflow_ingest


def run(day=None, limit=None):
    day = day or (datetime.now(ZoneInfo('Australia/Sydney')).date() - timedelta(days=1)).isoformat()
    datetime.strptime(day, '%Y-%m-%d')
    source = XMLSource()
    source.load_identities()
    def index_batch(batch):
        if not batch:
            return 0
        if os.getenv('DAILY_HANSARD_WORKFLOW_ID'):
            workflow_ingest(batch, day)
            return len(batch)
        return bulk('hansard', batch, 'speech_id')
    count, raw = 0, []
    for house in ('representatives', 'senate'):
        batch = []
        documents, report = source.day(day, house)
        raw.append(report)
        for doc in documents:
            if doc and (limit is None or count + len(batch) < limit):
                batch.append(doc)
            if len(batch) == 100:
                count += index_batch(batch)
                batch = []
            if limit is not None and count + len(batch) >= limit:
                break
        count += index_batch(batch)
        if limit is not None and count >= limit:
            break
    payload = json.dumps(raw, ensure_ascii=False)
    raw_dir = ROOT / 'ingest/raw'
    raw_dir.mkdir(exist_ok=True)
    # A capped backfill must not overwrite a previous full raw snapshot.
    suffix = '.partial' if limit is not None else ''
    (raw_dir / f'{day}{suffix}.json').write_text(payload, encoding='utf-8')
    if os.getenv('S3_RAW_BUCKET'):
        import boto3
        boto3.client('s3', region_name=os.getenv('AWS_REGION', 'ap-southeast-2')).put_object(
            Bucket=os.environ['S3_RAW_BUCKET'], Key=f'hansard/raw/{day}{suffix}.json',
            Body=payload.encode(), ContentType='application/json')
    print(f'{day}: indexed {count} speeches', flush=True)
    return {'date': day, 'indexed': count}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date')
    args = parser.parse_args()
    run(args.date)
