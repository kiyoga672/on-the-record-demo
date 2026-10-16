import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest import backfill


class Source:
    def load_identities(self):
        pass

    def dates(self, house):
        return ['2026-10-15']

    def day(self, day, house):
        return [{'speech_id': f'{house}:1'}], {
            'parsed': 1, 'quarantined': 1 if house == 'senate' else 0, 'sha256': 'fixture'}


class BackfillTest(unittest.TestCase):
    def test_resume_and_whole_day_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(backfill, 'ROOT', Path(directory)), \
                 patch.object(backfill, 'XMLSource', Source), \
                 patch.object(backfill, 'bulk', side_effect=lambda i, docs, field: len(docs)) as bulk, \
                 patch.object(backfill, 'request', return_value={'count': 2}), \
                 patch.object(backfill.time, 'sleep'):
                first = backfill.run(limit=1)
                self.assertEqual(first['indexed_this_run'], 1)
                second = backfill.run(limit=1)
                self.assertEqual(second['indexed_this_run'], 1)
                third = backfill.run(limit=1)
                self.assertEqual(third['indexed_this_run'], 0)
                self.assertEqual(bulk.call_count, 2)
                manifest = json.loads((Path(directory) / '.local/coverage.json').read_text())
                self.assertFalse(manifest['complete'])  # Quarantine must not become full coverage.
                self.assertFalse((Path(directory) / '.local/backfill.lock').exists())

    def test_indexing_interruption_is_not_skipped(self):
        self.assertFalse(backfill.covered({'status': 'indexing', 'parsed': 2, 'indexed': 1, 'sha256': 'x'}))
        self.assertFalse(backfill.covered({'status': 'source_missing', 'parsed': 0, 'indexed': 0}))


if __name__ == '__main__':
    unittest.main()
