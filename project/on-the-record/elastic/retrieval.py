"""Canonical Python hybrid query, mirrored in ui/lib/elastic.ts."""
import os


def hybrid_query(speaker_id, topic, size=8):
    filters = [{'term': {'speaker_id': speaker_id}}, {'range': {'date': {'gte': '2025-01-01'}}}]
    lexical = {'standard': {'query': {'bool': {'should': [{'match': {'text': {'query': topic}}},
        {'match_phrase': {'debate_title': topic}}], 'minimum_should_match': 1, 'filter': filters}}}}
    semantic = {'standard': {'query': {'bool': {'must': [{'semantic': {'field': 'semantic_body', 'query': topic}}], 'filter': filters}}}}
    fusion = {'rrf': {'retrievers': [lexical, semantic], 'rank_window_size': 40, 'rank_constant': 60}}
    return {'size': size, 'retriever': {'text_similarity_reranker': {'retriever': fusion, 'field': 'text',
        'inference_id': os.getenv('RERANK_INFERENCE_ID', '.rerank-v1-elasticsearch'), 'inference_text': topic,
        'rank_window_size': 20}}, '_source': ['speech_id', 'speaker_id', 'speaker_name', 'date', 'house', 'party', 'debate_title', 'text', 'url']}
