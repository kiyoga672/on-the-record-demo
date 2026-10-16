"""Native Kibana 9.5 dashboard, live ES|QL metrics rather than static success claims."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, request, required


def run():
    metrics = [
      ('Delivered quotes verified (%)', 'FROM eval_runs | STATS verified=SUM(quotes_verified), total=SUM(quotes_total) | EVAL value=CASE(total > 0, 100.0 * verified / total, null) | KEEP value'),
      ('Full-coverage refusal accuracy (%) — null until coverage complete', 'FROM eval_runs | WHERE expected == "unanswerable" | STATS value=AVG(CASE(refusal_correct == true, 100.0, refusal_correct == false, 0.0, null))'),
      ('Median end-to-end latency (ms)', 'FROM eval_runs | STATS value=PERCENTILE(latency_ms, 50)'),
      ('Answerable cases with verified answers (%)', 'FROM eval_runs | WHERE expected == "answerable" | STATS value=AVG(CASE(answer_correct == true, 100.0, 0.0))'),
      ('Evaluated cases', 'FROM eval_runs | STATS value=COUNT(*)'),
      ('Delivered quote count (denominator)', 'FROM eval_runs | STATS value=SUM(quotes_total)')
      ,('Indexed-scope negative controls correct (%)', 'FROM eval_runs | WHERE expected == "unanswerable" | STATS value=AVG(CASE(indexed_scope_refusal_correct == true, 100.0, 0.0))')
    ]
    definition = {'title': 'On the Record — reliability',
        'description': 'Live metrics over eval_runs. Provisional cases cover indexed material only. A null full-coverage refusal metric is intentional. Delivered quote verification is not raw-agent groundedness; unavailable cases count against answerable-case success. Bedrock judge not run.',
        'panels': [{'type': 'vis', 'grid': {'x': (i % 3) * 16, 'y': (i // 3) * 9, 'w': 16, 'h': 9},
                    'config': {'title': title, 'type': 'metric', 'data_source': {'type': 'esql', 'query': query},
                               'metrics': [{'type': 'primary', 'column': 'value'}]}}
                   for i, (title, query) in enumerate(metrics)]}
    for _, query in metrics:
        request('es', 'POST', '/_query', {'query': query})
    (ROOT / 'elastic/reliability-dashboard.json').write_text(json.dumps(definition, indent=2), encoding='utf-8')
    result = request('kibana', 'PUT', '/api/dashboards/on-the-record-reliability', definition)
    print('Dashboard ready:', required('KIBANA_URL').rstrip('/') + '/app/dashboards#/view/on-the-record-reliability')
    print('Response keys:', list(result))


if __name__ == '__main__':
    run()
