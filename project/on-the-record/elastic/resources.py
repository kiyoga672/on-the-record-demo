"""Deterministic source definitions, also exported as reviewable JSON files."""
from pathlib import Path
import json

BASE = Path(__file__).parent
START = '2025-01-01T00:00:00Z'


def mapping(fields):
    return {'mappings': {'properties': fields}}


def kw():
    return {'type': 'keyword'}


MAPPINGS = {
    'saved_quotes': mapping({**{k: kw() for k in ['email', 'speaker_id', 'speaker_name', 'party', 'topic',
        'quote_hash', 'house', 'url', 'management_hash', 'speech_id', 'record_kind']},
        'quote': {'type': 'text'}, 'monthly': {'type': 'boolean'},
        **{k: {'type': 'date'} for k in ['date', 'remind_on', 'created_at', 'sent_at', 'last_sent']}}),
    'hansard': mapping({**{k: kw() for k in ['speech_id', 'house', 'speaker_id', 'party', 'electorate', 'topic_tag', 'url']},
        'date': {'type': 'date'}, 'speaker_name': {'type': 'keyword', 'fields': {'text': {'type': 'text'}}},
        'debate_title': {'type': 'text', 'fields': {'kw': kw()}},
        'text': {'type': 'text', 'copy_to': 'semantic_body'},
        'semantic_body': {'type': 'semantic_text', 'inference_id': '.elser-2-elasticsearch'},
        'word_count': {'type': 'integer'}}),
    'members': mapping({**{k: kw() for k in ['person_id', 'house', 'party', 'electorate', 'state', 'image_url']},
                        'name': {'type': 'keyword', 'fields': {'text': {'type': 'text'}}}}),
    'watches': mapping({**{k: kw() for k in ['email', 'speaker_name', 'speaker_id', 'topic']},
                       **{k: {'type': 'date'} for k in ['created_at', 'last_sent']}}),
    'eval_runs': mapping({**{k: kw() for k in ['run_id', 'expected']}, 'timestamp': {'type': 'date'},
                         'question': {'type': 'text'},
                         **{k: {'type': 'integer'} for k in ['quotes_total', 'quotes_verified', 'latency_ms']},
                         **{k: {'type': 'boolean'} for k in ['refusal_correct', 'judge_grounded']}})
}

QUERIES = {
 'verify_quote': ('Locate a phrase candidate by speaker. Returns original text for a mandatory exact substring check; phrase matching alone is NOT proof.',
  'FROM hansard | WHERE speaker_id == ?speaker_id AND date >= TO_DATETIME(?from) AND MATCH_PHRASE(text, ?quote) | KEEP speech_id, speaker_id, text, date, house, url | LIMIT 10', ['speaker_id','quote','from']),
 'speaker_topics': ('List debate titles this person has spoken on, without inferring their views.',
  'FROM hansard | WHERE speaker_id == ?speaker_id AND date >= TO_DATETIME(?from) | STATS speeches = COUNT(*) BY debate_title.kw | SORT speeches DESC | LIMIT 10', ['speaker_id','from']),
 'topic_timeline': ('Monthly counts of speeches containing a topic by a speaker.',
  'FROM hansard | WHERE speaker_id == ?speaker_id AND date >= TO_DATETIME(?from) AND MATCH(text, ?topic) | STATS n = COUNT(*) BY month = DATE_TRUNC(1 month, date) | SORT month | LIMIT 1000', ['speaker_id','topic','from']),
 'topic_attention': ('Counts and topic share across eligible speakers in one house. Frequency is not a political position. UI must check coverage before scoring.',
  'FROM hansard | WHERE house == ?house AND date >= TO_DATETIME(?from) | STATS total = COUNT(*), on_topic = COUNT(*) WHERE MATCH(text, ?topic) BY speaker_id, speaker_name | WHERE total >= 5 | EVAL share = TO_DOUBLE(on_topic) / TO_DOUBLE(total) | SORT share DESC | LIMIT 10000', ['house','topic','from']),
 'topic_by_party': ('Counts of topic mentions per party. Not a position or character judgement.',
  'FROM hansard | WHERE house == ?house AND date >= TO_DATETIME(?from) | STATS total = COUNT(*), on_topic = COUNT(*) WHERE MATCH(text, ?topic) BY party | LIMIT 1000', ['house','topic','from'])
}


def tools():
    result = [{'id': 'search_speeches', 'type': 'index_search', 'description':
       'Search Hansard ONLY for the specified speaker_id and topic since 2025-01-01. Return speech_id, text, date, house, debate_title, url. Never infer opinions.',
       'configuration': {'pattern': 'hansard'}}]
    for name, (description, query, params) in QUERIES.items():
        result.append({'id': name, 'type': 'esql', 'description': description,
          'configuration': {'query': query, 'params': {p: {'type': 'string', 'description': p,
              **({'optional': True, 'defaultValue': START} if p == 'from' else {})} for p in params}}})
    return result


def export():
    for index, body in MAPPINGS.items():
        p = BASE / 'mappings' / f'{index}.json'
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(body, indent=2), encoding='utf-8')
    for tool in tools():
        p = BASE / 'tools' / f'{tool["id"]}.json'
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(tool, indent=2), encoding='utf-8')
    p = BASE / 'inference/rerank.json'
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({'inference_id': '.rerank-v1-elasticsearch', 'service': 'elasticsearch',
                            'note': 'Uses the existing Hosted default; setup checks rather than replaces it.'}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    export()
