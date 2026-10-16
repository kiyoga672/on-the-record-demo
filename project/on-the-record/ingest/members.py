import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import bulk
from ingest.oa_client import OpenAustralia
from urllib.parse import urljoin


def run():
    api = OpenAustralia()
    count = 0
    for function, house in [('getRepresentatives', 'House'), ('getSenators', 'Senate')]:
        rows = api.get(function)
        if not isinstance(rows, list):
            raise RuntimeError(f'{function}: expected a list; inspect response shape')
        docs = [{'person_id': str(r['person_id']), 'name': r.get('name', ''), 'house': house,
                 'party': r.get('party', ''), 'electorate': r.get('constituency', ''),
                 'state': r.get('state') or (r.get('constituency', '') if house == 'Senate' else ''),
                 'image_url': urljoin('https://www.openaustralia.org.au/', r.get('image', ''))} for r in rows]
        count += bulk('members', docs, 'person_id')
    print(f'Indexed {count} members')


if __name__ == '__main__':
    run()
