"""No network and no mail: verify scheduling, exact formatting and state transitions."""
import unittest
from datetime import datetime, timezone
from reminder_worker import due, message, deliver, ATTRIBUTION

NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)
DOC = dict(email='test@example.invalid', record_kind='quote', quote_hash='abc', speaker_name='Example Member',
    party='Example', topic='housing', quote='An exact statement.', date='2026-10-15', house='representatives',
    url='https://www.openaustralia.org.au/debates/?id=example', remind_on='2026-10-20', monthly=False,
    sent_at=None, last_sent=None)


class DigestTest(unittest.TestCase):
    def test_due_and_repeat(self):
        self.assertTrue(due(DOC, NOW))
        self.assertFalse(due({**DOC, 'sent_at': '2026-11-01T00:00:00Z'}, NOW, True))
        self.assertFalse(due({**DOC, 'remind_on': '2027-01-01'}, NOW))
        self.assertTrue(due({**DOC, 'remind_on': '2027-01-01'}, NOW, True))
        self.assertFalse(due({'record_kind': 'ownership'}, NOW, True))

    def test_monthly(self):
        doc = {**DOC, 'monthly': True, 'last_sent': '2026-10-20T00:00:00Z'}
        self.assertTrue(due(doc, NOW))
        self.assertFalse(due(doc, NOW.replace(day=2)))
        self.assertTrue(due(doc, NOW.replace(day=2), True))
        self.assertFalse(due({**doc, 'last_sent': '2026-11-01T00:00:00Z'}, NOW, True))

    def test_exact_formatting(self):
        body = message([DOC, {**DOC, 'quote': 'Newer quote.', 'date': '2026-10-16'}])
        self.assertLess(body.index('Newer quote.'), body.index(DOC['quote']))
        self.assertIn('15 Oct 2026, House — ' + DOC['url'], body)
        self.assertIn('"' + DOC['quote'] + '"', body)
        self.assertIn(ATTRIBUTION, body)

    def test_success_and_ambiguous_retry_guard(self):
        calls = []
        def transport(service, method, path, body):
            calls.append((service, path, body))
            if path.endswith('_mget'):
                return {'docs': [{'_id': 'test', '_source': DOC, 'found': True}]}
            return {'status': 'ok'} if service == 'kibana' else {'result': 'updated'}
        self.assertTrue(deliver([{'_id': 'test', '_source': DOC}], NOW, 'testconnector', transport))
        self.assertEqual(len(calls), 5)
        self.assertEqual(calls[3][2]['doc']['sent_at'], '2026-11-01T00:00:00Z')
        self.assertFalse(deliver([{'_id': 'test', '_source': DOC}], NOW, 'testconnector', lambda *a: {'result': 'noop'}))

    def test_failed_connector_never_marks_sent_or_releases_claim(self):
        calls = []
        def transport(service, method, path, body):
            if path.endswith('_mget'):
                return {'docs': [{'_id': 'test', '_source': DOC, 'found': True}]}
            calls.append(service)
            return {'status': 'error'} if service == 'kibana' else {'result': 'updated'}
        with self.assertRaises(RuntimeError):
            deliver([{'_id': 'test', '_source': DOC}], NOW, 'testconnector', transport)
        self.assertEqual(calls, ['es', 'kibana'])

    def test_stale_selection_does_not_resend(self):
        calls = []
        def transport(service, method, path, body):
            calls.append(service)
            if path.endswith('_mget'):
                return {'docs': [{'_id': 'test', '_source': {**DOC, 'sent_at': '2026-11-01T00:00:00Z'}, 'found': True}]}
            return {'result': 'updated'}
        self.assertFalse(deliver([{'_id': 'test', '_source': DOC}], NOW, 'testconnector', transport))
        self.assertNotIn('kibana', calls)


if __name__ == '__main__':
    unittest.main()
