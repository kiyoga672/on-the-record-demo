# AWS and Elastic demo deployment

## Already checked

- AWS Sydney Elastic Cloud Hosted 9.5.5.
- Bedrock activity tool created 14 `amazonbedrock` inference endpoints, configured region ap-southeast-2.
- `BEDROCK_INFERENCE_ID=bedrock-sonnet-4-5-chat`; this is not a Kibana connector ID.
- ML node present; ELSER and Elastic Rerank minimal calls passed after first-load delay.

## Not deployed yet

### What the account owner needs to prepare

- An AWS account or hackathon-provided AWS console session with a role permitted to deploy the demo. The Elastic API key authorizes Elastic, not S3/Lambda/SES/IAM. Bedrock activity endpoint access alone does not establish these AWS permissions.
- Region `ap-southeast-2`. Prefer local AWS CLI SSO or the event's temporary credentials; keep credentials out of chat and source control. See https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html .
- Deployment permissions scoped to this application's S3 bucket, Lambda, EventBridge Scheduler, CloudWatch logs and required IAM roles/PassRole. Runtime roles should be narrower: raw-prefix S3 PutObject, logs, required secret reads, and SES SendEmail only if the chosen mail path uses the SDK.
- A sender email address or domain for SES, plus a test recipient. Sender identity verification is required; sandbox accounts also require verified recipients. See https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html . Email verification and production access are account-owner steps.
- Before Guardrails integration, confirm the activity-managed Elastic-to-Bedrock route exposes the required guardrail parameters. A Guardrail ID in .env alone does not enable filtering.

Historical backfill runs locally using the existing Elastic configuration and does not require AWS credentials. Local XML evidence is archived before indexing. AWS configuration can proceed independently of backfill.

- Amplify: use a supported Next.js release with SSR/API routes; build from `on-the-record/ui`. Current implementation uses Next.js 16.4.2 because npm audit reported unpatched critical vulnerabilities in 14.2.35. Verify Amplify's current framework support before selecting hosting; do not assume compatibility.
- Configure ES_URL/KIBANA_URL/ES_API_KEY/AGENT_ID/BEDROCK_INFERENCE_ID and workflow IDs as server-side environment variables. Never prefix secrets with NEXT_PUBLIC_. Coverage manifest currently resides on disk and must be deployed or moved to a durable metadata store; missing manifest deliberately means incomplete coverage.
- Lambda: package `common.py`, `ingest/`, requirements into deployment root; use `ingest.lambda_handler.handler`. daily.py uses the verified XML parser and, when configured, submits batches to the daily_hansard Workflow. Deploy and test it with AWS IAM before enabling a schedule. Function URL uses a bearer token and must not be published unprotected.
- Scheduler: use EventBridge Scheduler with `cron(0 6 * * ? *)` and timezone `Australia/Sydney`, not fixed UTC for a year-round 06:00 schedule.
- S3: optional raw-source archive, least-privilege PutObject, versioning/retention for immutable evidence. Local source files are currently archived before indexing by xml_source.py.
- SES: verify sender/recipient under sandbox limits and configure Kibana email connector. Existing `elastic-cloud-email` is not established as SES. No emails have been sent by this project.
- Guardrails: configure against the actual Bedrock invocation path, verify support before claiming active protection. No Guardrail ID is configured yet.

## Workflow readiness

Four manually triggered Workflows are registered: otr-find-my-mp, otr-follow-topic, otr-export-factsheet, otr-daily-hansard. Member lookup, verified export and a source-record ingestion replay have confirmed completed executions. Follow saves a watch; scheduling, matching and email automation are not live yet.

Before public hosting, complete postcode mapping, ingestion scheduling, coverage integrity, unsubscribe/access controls and outbound email limits. The current preview is local-only.
