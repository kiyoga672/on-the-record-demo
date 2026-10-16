# On the Record

LLM for reasoning, Elastic for truth.

A local demo for source-verified Australian federal parliamentary quotations. The query/export path works against real data; full data coverage and daily email automation are not complete. See [PLAN.md](PLAN.md) for actual status and remaining acceptance gates.

## Run locally

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r on-the-record\ingest\requirements.txt
# Only when .env does not already exist:
Copy-Item .env.example .env
.\.venv\Scripts\python.exe on-the-record\elastic\preflight.py --warm
.\.venv\Scripts\python.exe on-the-record\elastic\setup.py
.\.venv\Scripts\python.exe on-the-record\ingest\members.py
.\.venv\Scripts\python.exe on-the-record\ingest\seed.py --days 1
Set-Location on-the-record\ui
npm.cmd ci
npm.cmd run build
npm.cmd run start
```

Open http://127.0.0.1:3000 . An already indexed demonstration is Bridget McKenzie → housing. Stop the running production server before rebuilding on Windows; the development server supports hot updates via npm.cmd run dev.

The shared root .env is loaded by Python and next.config.mjs. Use ES_URL, KIBANA_URL, ES_API_KEY, OPENAUSTRALIA_KEY and BEDROCK_INFERENCE_ID. For this deployment BEDROCK_INFERENCE_ID is bedrock-sonnet-4-5-chat; it is not a connector ID. setup.py registers workflows when this variable is configured. Secrets never use NEXT_PUBLIC_ and are ignored by Git.

## Implemented and verified

- Elastic Cloud Hosted 9.5.5, AWS Sydney, ML node present.
- semantic_text explicitly uses .elser-2-elasticsearch. BM25 + ELSER with RRF, then .rerank-v1-elasticsearch. Both inference endpoints tested after warm-up.
- Agent Builder selects candidate excerpts via Bedrock Claude Sonnet. The timeline uses the streaming converse API with a restricted verify_quote tool set.
- Every delivered quote calls verify_quote and passes a fresh source read for speaker, date, chamber, trusted URL, <=60 words and exact continuous text.
- A speech is deduplicated only after an excerpt passes verification. A rejected first excerpt cannot hide a valid later excerpt from the same speech. Verification failures are retryable and are not retained in the five-minute finding cache. `eval/check_recommended_search.py` checks both a short debate heading and a long bill-title recommendation against fresh source text.
- After hybrid ranking, relevance evidence may come from conservative body vocabulary or a source debate-heading phrase. Common themes expand body synonyms; unknown multiword body topics require all terms. Heading-derived recommendations do not require speakers to repeat the heading in their speech. This may omit implicit discussion and is not proof of global absence.
- Six custom retrieval/analysis tools and three Workflow tools are assigned to the agent.
- Four Workflows registered: member lookup, follow storage, fact-sheet candidate generation, worker-triggered batch ingestion. Lookup, export and source-record replay have real completed executions. Follow saves a watch but daily digest delivery is not live.
- Next.js 16.4.2 / React 19 / Tailwind 4 / Recharts 3. The brief's Next.js 14.2.35 had unpatched critical advisories in npm audit, so it was replaced. Current dependency audit reports zero vulnerabilities.
- Homepage/name lookup, speaker/debate chips, verified timeline, original links, attention/monthly UI, follow modal and verified markdown export.
- Kibana dashboard on-the-record-reliability uses live ES|QL over eval_runs. It separates delivered-quote verification, positive-case success and indexed-scope negative controls. Full-Hansard refusal accuracy stays null until coverage supports it.

## Current data and limitations

226 members are indexed. The initial seed contained 542 speeches from both houses on 2026-10-15; historical backfill is now being performed in bounded runs. Read the live index count and `.local/coverage.json` for current progress. Coverage is explicitly incomplete, so absence is reported only within the indexed material. Attention's chamber comparison remains unavailable; the monthly chart and raw counts work.

Resume historical data from the repository root:

```powershell
.\.venv\Scripts\python.exe on-the-record\ingest\backfill.py --since 2025-01-01 --limit 6000 --batch-size 20
```

The limit is the document budget per run. Complete source days are processed newest first across both chambers; a day larger than the remaining budget is deferred. Completed days, including explicitly quarantined source records, are skipped on subsequent runs. Interrupted days are replayed with stable IDs. Only one backfill may run at a time; a force-killed process may leave `.local/backfill.lock`, which should be removed only after confirming that process has stopped. Do not run seed.py concurrently. Raw archives remain local unless S3_RAW_BUCKET is configured. Partial/quarantined coverage never enables full-coverage claims.

OpenAustralia getRepresentative accepts id/division, not postcode. A verified postcode/electorate map is still required. Source search APIs returned HTTP 500; the ingestion implementation uses the source's verified public XML fallback. It joins term IDs through people.xml rather than guessing names. Raw XML is archived before indexing, and seed.py records coverage/counts/hashes under .local/coverage.json.

No mail was sent. Scheduled ingest, topic classification, watch matching, unsubscribe/access controls, SES, Guardrails, S3 retention and public Amplify deployment remain pending. Daily ingestion uses Elastic Workflows for batches when DAILY_HANSARD_WORKFLOW_ID is configured, but this is not a scheduled digest service yet.

## Sharing, templates and saved quotes

- `/speaker/10758?topic=housing` reproduces the verified query. Searches and debate chips update the topic URL. Metadata and `/api/og?speaker_id=10758&topic=housing` share a bounded five-minute result cache and the existing verification pipeline. Set server-side `SITE_URL` to the public origin after deployment. Localhost links work only on this computer.
- Share to X, Facebook, WhatsApp and LinkedIn; copy a link, use native sharing, or open the quote card for an Instagram hand-off. There is no share-event logging or tracking parameter.
- Sharing with contacts uses the device share sheet and the optional Web Contact Picker API; On the Record does not upload, store or log contacts. Explicitly chosen recipients are passed only to the user's own mail/SMS app. Native capabilities require a supporting browser/device; no real-device verification has been performed.
- Write to your MP and Draft a petition preserve up to three source-exact quotes and leave the user's request as a placeholder. Public official contact email is returned only when supplied by OpenAustralia with an aph.gov.au domain; otherwise the official parliamentary lookup is linked. Long drafts use copying rather than shortening a quotation. Nothing is submitted by the app.
- Save quote calls `verify_quote` plus a fresh source read, then the native `save_quote` Workflow rechecks source and ownership. Repeated saves preserve one record and do not reset delivery state. The `/saved` interface can list/remove quotes in the original browser. A random browser management key protects access; email alone is insufficient. The UI sends personal email in a POST body, not a URL. Remove all also deletes the ownership/email record, unless delivery is pending.
- `NEXT_PUBLIC_REMINDER_DEFAULT` is an optional date in YYYY-MM-DD form (example 2028-04-01 is configurable, not an election prediction); absent/expired configuration defaults to 30 days ahead.
- `otr-reminder-digest` is a complete native no-LLM definition, registered DISABLED pending EMAIL_CONNECTOR_ID and an authorized delivery test. Never enable it merely because YAML validates. Manual immediate-send means pending one-off quotes irrespective of reminder date, with monthly same-month guards. Delivery claims require reconciliation after an ambiguous failure to avoid blind duplicate retries. The worker `elastic/workflows/reminder_worker.py` defaults to count-only dry-run; real sends are opt-in. No email has been sent. Native digest runs are bounded to 1,000 recipient groups and 1,000 quotes per recipient; production pagination is still required. Elastic execution details may retain inputs and outputs, including email content; configure access control and retention before public use.
- Live API evidence is in ignored `.local/feature-api-check.json`; preview card in `.local/feature-quote-card.png`. Full check details and unavailable acceptance tests are in FEATURE_BACKLOG.md.

## Checks and evaluation

```powershell
.\.venv\Scripts\python.exe -m compileall -q on-the-record
.\.venv\Scripts\python.exe on-the-record\ingest\test_xml_source.py
.\.venv\Scripts\python.exe on-the-record\elastic\readiness.py
npm.cmd --prefix on-the-record\ui run typecheck
npm.cmd --prefix on-the-record\ui test
.\.venv\Scripts\python.exe on-the-record\eval\build_golden.py
.\.venv\Scripts\python.exe on-the-record\eval\run_eval.py
.\.venv\Scripts\python.exe on-the-record\elastic\dashboard.py
```

The golden set has 10 real-index positive cases and 5 artificial negative controls. It is provisional and covers indexed material only. Historical failures are retained. A positive regression returned verified answers for 9/10 cases, with 10/10 delivered quotes matching source text; after topic-gating/empty-state fixes all 5 indexed-scope negatives returned no quotes and disclosed incomplete coverage. This does not establish 100% overall answer accuracy or full-Hansard refusal accuracy. The Bedrock LLM judge has not run.

## Source and neutrality

Source: Parliament of Australia Hansard via OpenAustralia.

The product shows verbatim quotations, dates, chambers and links. It does not paraphrase political positions, score character or infer party views. Source licence conditions are linked from the OpenAustralia API documentation; review redistribution conditions before public release. No user analytics or unrequested postcode storage.

## References

- [OpenAustralia API](https://www.openaustralia.org.au/api/)
- [Agent Builder tools](https://www.elastic.co/docs/api/doc/kibana/operation/operation-post-agent-builder-tools)
- [Workflow run API](https://www.elastic.co/docs/api/doc/kibana/operation/operation-post-workflows-workflow-id-run)
- [AWS deployment notes](infra/aws_notes.md)
