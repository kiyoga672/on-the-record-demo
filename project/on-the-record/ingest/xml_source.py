"""OpenAustralia source fallback: source XML, identity joins and reproducible archives."""
import hashlib
import json
import time
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, quote
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from common import ROOT

BASE = 'https://data.openaustralia.org.au/'


class XMLSource:
    def __init__(self):
        self.session = requests.Session()
        self.last_call = 0
        self.identities = {}
        self.people = {}
        self.members = {}

    def fetch(self, path, *, missing_ok=False):
        time.sleep(max(0, .55 - (time.monotonic() - self.last_call)))
        self.last_call = time.monotonic()
        for attempt in range(4):
            try:
                response = self.session.get(urljoin(BASE, path), timeout=(15, 60))
            except requests.RequestException:
                raise RuntimeError('Source XML network error') from None
            if response.status_code == 404 and missing_ok:
                return None
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            if not response.ok:
                raise RuntimeError(f'Source XML HTTP {response.status_code}: {path}')
            data = response.content
            archive = ROOT / 'ingest/raw' / (path + 'index.html' if path.endswith('/') else path)
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_bytes(data)  # Archive before parsing/indexing.
            if os.getenv('S3_RAW_BUCKET') and path.endswith('.xml'):
                import boto3
                boto3.client('s3', region_name=os.getenv('AWS_REGION', 'ap-southeast-2')).put_object(
                    Bucket=os.environ['S3_RAW_BUCKET'], Key='hansard/raw/' + path,
                    Body=data, ContentType='application/xml')
            return data

    def load_identities(self):
        root = ET.fromstring(self.fetch('members/people.xml'))
        for person in root.findall('person'):
            pid = person.attrib['id'].rsplit('/', 1)[-1]
            self.people[pid] = person.get('latestname', '')
            for office in person.findall('office'):
                self.identities[office.get('id')] = pid
        for name in ('representatives', 'senators'):
            for member in ET.fromstring(self.fetch(f'members/{name}.xml')).findall('member'):
                self.members[member.get('id')] = member.attrib

    def dates(self, house):
        path = f'scrapedxml/{house}_debates/'
        page = self.fetch(path)
        links = BeautifulSoup(page, 'html.parser').find_all('a')
        return sorted({a['href'][:10] for a in links if len(a.get('href', '')) == 14 and a['href'].endswith('.xml')}, reverse=True)

    def day(self, day, house):
        path = f'scrapedxml/{house}_debates/{day}.xml'
        payload = self.fetch(path, missing_ok=True)
        if payload is None:
            return [], {'date': day, 'house': house, 'status': 'source_missing', 'parsed': 0, 'quarantined': 0}
        root = ET.fromstring(payload)
        major, minor, docs, skipped = '', '', [], []
        for entry in root:
            tag = entry.tag
            text = BeautifulSoup(ET.tostring(entry, encoding='unicode'), 'html.parser').get_text(' ', strip=True)
            if tag == 'major-heading':
                major, minor = text, ''
            elif tag == 'minor-heading':
                minor = text
            elif tag == 'speech':
                sid = entry.get('speakerid')
                pid = self.identities.get(sid)
                if not pid or sid not in self.members:
                    skipped.append(entry.get('id'))
                    continue
                term = self.members[sid]
                gid = entry.get('id', '').split('/')[-1]
                # Preserve paragraph boundaries as spaces, same convention as the API normalizer.
                text = ' '.join(' '.join(p.itertext()).strip() for p in entry if p.tag not in ('division',))
                text = ' '.join(text.split())
                if not text:
                    continue
                docs.append({'speech_id': f'{house}:{gid}', 'date': day,
                    'house': 'Senate' if house == 'senate' else 'House', 'speaker_id': pid,
                    'speaker_name': entry.get('speakername') or self.people.get(pid, ''),
                    'party': term.get('party', ''), 'electorate': term.get('division', ''),
                    'debate_title': ' — '.join(filter(None, [major, minor])), 'text': text,
                    'url': f'https://www.openaustralia.org.au/{"senate" if house == "senate" else "debates"}/?id={quote(gid)}',
                    'word_count': len(text.split())})
        return docs, {'date': day, 'house': house, 'status': 'parsed', 'parsed': len(docs),
                      'source_speeches': len(root.findall('speech')), 'quarantined': len(skipped),
                      'quarantined_ids': skipped, 'sha256': hashlib.sha256(payload).hexdigest(),
                      'source_url': urljoin(BASE, path), 'fetched_at': datetime.now(timezone.utc).isoformat(),
                      'parser_version': 1}
