# On the Record — Amplify release

Source-verified Australian parliamentary quotations.

This standalone release preserves the current demo features on Amplify-supported Next.js 15.5.28 and Node.js 22. The original working checkout uses Next.js 16 and remains unchanged. PostCSS is overridden to patched 8.5.30.

See DEPLOYMENT.md and amplify.yml for deployment steps. Configure service credentials only in the AWS console. No secrets are included in this repository. Reminder email delivery remains disabled pending connector configuration and authorized testing. Index coverage remains incomplete.

Source: Parliament of Australia Hansard via OpenAustralia.

## Complete current project source

The `project/` directory contains the current local application and backend source: Next.js 16 UI, Python ingestion, Elastic mappings and Workflows, evaluation scripts and development documentation. Start with `project/on-the-record/README.md`; copy `project/.env.example` to `project/.env` and supply your own credentials. Raw data, local reports, credentials and dependencies are excluded.

The repository root remains the independent Next.js 15/Node.js 22 Amplify compatibility copy. Its interface and attention-score logic are synchronized, but it has not been deployed to AWS. Local demo operation uses `project/on-the-record/ui`.

Topic Attention can show a provisional score computed from indexed data with an explicit incomplete-coverage label. A score still requires at least five speeches for the selected speaker, at least two eligible peers, and a nonzero median. Example: 50 denotes the eligible-speaker median topic share; 100 is at least twice that median. The score measures speech frequency, not political positions or quality. Seventeen frontend tests pass, including the sample and zero-median guards.
