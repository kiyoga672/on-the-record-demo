import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest.xml_source import XMLSource


class XMLParserTest(unittest.TestCase):
    def test_identity_join_and_quarantine(self):
        source = XMLSource()
        source.identities = {'uk.org.publicwhip/member/7': '10007'}
        source.members = {'uk.org.publicwhip/member/7': {'party': 'Fixture', 'division': 'Fixture'}}
        payload = b'<publicwhip><major-heading>Debate</major-heading><minor-heading>Topic</minor-heading><speech id="uk.org.publicwhip/debate/2026-10-15.1.1" speakerid="uk.org.publicwhip/member/7" speakername="Fixture"><p>Exact <i>words</i> here.</p></speech><speech id="unknown" speakerid="missing"><p>Must not misattribute.</p></speech></publicwhip>'
        with patch.object(source, 'fetch', return_value=payload):
            docs, report = source.day('2026-10-15', 'representatives')
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]['speaker_id'], '10007')
        self.assertEqual(docs[0]['text'], 'Exact words here.')
        self.assertEqual(docs[0]['debate_title'], 'Debate — Topic')
        self.assertEqual(report['quarantined'], 1)
        self.assertEqual(report['source_speeches'], 2)


if __name__ == '__main__':
    unittest.main()
