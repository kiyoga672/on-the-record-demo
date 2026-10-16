"""OpenAustralia client with pacing, bounded retries, and explicit response validation."""
import time
from datetime import date
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from common import required


class OpenAustralia:
    def __init__(self):
        self.session = requests.Session()
        self.last_call = 0.0

    def get(self, function, **params):
        if sum(p in params for p in ('search', 'person', 'date')) > 1:
            raise ValueError('Use only one of search, person, date')
        for attempt in range(5):
            time.sleep(max(0, .55 - (time.monotonic() - self.last_call)))
            self.last_call = time.monotonic()
            try:
                response = self.session.get(f'https://www.openaustralia.org.au/api/{function}',
                    params={'key': required('OPENAUSTRALIA_KEY'), 'output': 'js', **params}, timeout=45)
            except requests.RequestException:
                raise RuntimeError('OpenAustralia connection failed (credentials hidden)') from None
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(min(30, 2 ** attempt))
                continue
            if not response.ok:
                raise RuntimeError(f'OpenAustralia {function}: HTTP {response.status_code}')
            data = response.json()
            if isinstance(data, dict) and data.get('error'):
                # Non-sitting days can be returned as errors; never silently treat auth errors as no data.
                msg = str(data['error']).lower()
                if 'no debates' in msg or 'no results' in msg or 'no speeches' in msg:
                    return {'rows': [], 'info': {}}
                raise RuntimeError(f'OpenAustralia {function} returned an API error; inspect account/access')
            return data
        raise RuntimeError('OpenAustralia retries exhausted')

    def debates(self, house, **selection):
        page = 1
        while True:
            result = self.get('getDebates', type=house, num=100, page=page, **selection)
            rows = result.get('rows', []) if isinstance(result, dict) else result
            if not isinstance(rows, list):
                raise RuntimeError('Unexpected OpenAustralia rows shape; inspect first response')
            yield from rows
            info = result.get('info', {}) if isinstance(result, dict) else {}
            if not rows or len(rows) < 100 or (info.get('total_results') is not None and page * 100 >= int(info['total_results'])):
                return
            page += 1


def plain(value):
    return BeautifulSoup(value or '', 'html.parser').get_text(' ', strip=True)


def speech(row, house):
    speaker = row.get('speaker') or {}
    text = plain(row.get('body'))
    gid = row.get('gid')
    if not gid or not speaker.get('person_id') or not text:
        return None  # headings/procedural records are not speeches
    day = str(row.get('hdate', ''))[:10]
    date.fromisoformat(day)
    parent = row.get('parent') or {}
    return {'speech_id': str(gid), 'date': day, 'house': 'Senate' if house == 'senate' else 'House',
            'speaker_id': str(speaker['person_id']),
            'speaker_name': speaker.get('name') or ' '.join(filter(None, [speaker.get('first_name'), speaker.get('last_name')])),
            'party': speaker.get('party', ''), 'electorate': speaker.get('constituency', ''),
            'debate_title': plain(parent.get('body', '')), 'text': text, 'word_count': len(text.split()),
            'url': f'https://www.openaustralia.org.au/{"senate" if house == "senate" else "debates"}/?id={quote(str(gid), safe="")}'}
