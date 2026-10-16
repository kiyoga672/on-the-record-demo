"""Shared configuration and HTTP transport. Never log request URLs containing keys."""
from pathlib import Path
import json
import os
import time
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT.parent / '.env'
load_dotenv(ENV_PATH)
load_dotenv(ROOT / '.env')
ATTRIBUTION = 'Source: Parliament of Australia Hansard via OpenAustralia.'


class ServiceError(RuntimeError):
    def __init__(self, service, method, path, response):
        self.status = response.status_code
        detail = response.text[:4000]
        for name, value in os.environ.items():
            if any(part in name.upper() for part in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD')) and len(value) > 5:
                detail = detail.replace(value, '[REDACTED]')
        super().__init__(f'{service} {method} {path}: HTTP {self.status}: {detail[:1500]}')


def required(name):
    value = os.getenv(name, '').strip()
    if not value or value.startswith('<<'):
        raise RuntimeError(f'Missing {name}; set it in {ENV_PATH}')
    return value


def request(service, method, path, body=None, *, raw=False, allow=()):
    base = required('KIBANA_URL' if service == 'kibana' else 'ES_URL').rstrip('/')
    headers = {'Authorization': f'ApiKey {required("ES_API_KEY")}', 'kbn-xsrf': 'true',
               'Content-Type': 'application/x-ndjson' if raw else 'application/json'}
    for attempt in range(4):
        try:
            response = requests.request(method, base + '/' + path.lstrip('/'), headers=headers,
                                        data=body if raw else None, json=None if raw else body,
                                        timeout=(15, 180))
        except requests.RequestException:
            raise RuntimeError(f'{service} {method} {path}: connection failed (URL and credentials hidden)') from None
        if response.status_code in (429, 502, 503, 504) and method in ('GET', 'HEAD', 'PUT') and attempt < 3:
            time.sleep(2 ** attempt)
            continue
        if response.status_code in allow:
            return None
        if not response.ok:
            # Service errors can echo credentials or workflow contents. Report status only.
            raise ServiceError(service, method, path, response)
        return response.json() if response.content and method != 'HEAD' else {}


def bulk(index, documents, id_field):
    if not documents:
        return 0
    lines = []
    for doc in documents:
        lines += [json.dumps({'index': {'_index': index, '_id': str(doc[id_field])}}), json.dumps(doc)]
    result = request('es', 'POST', '/_bulk', '\n'.join(lines) + '\n', raw=True)
    failed = [item['index']['status'] for item in result.get('items', []) if item['index'].get('error')]
    if failed:
        raise RuntimeError(f'Bulk failed for {len(failed)} documents, statuses: {sorted(set(failed))}')
    return len(documents)
