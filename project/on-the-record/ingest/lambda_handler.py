"""Function URL authentication is required; never deploy an unprotected ingestion endpoint."""
import hmac
import json
import os
from ingest.daily import run


def handler(event, context):
    if 'requestContext' in event:
        expected = os.getenv('INGEST_FUNCTION_TOKEN', '')
        given = event.get('headers', {}).get('authorization', '')
        if not expected or not hmac.compare_digest(given, f'Bearer {expected}'):
            return {'statusCode': 401, 'body': 'Unauthorized'}
        payload = json.loads(event.get('body') or '{}')
    else:
        payload = event
    result = run(payload.get('date'))
    return {'statusCode': 200, 'body': json.dumps(result)}
