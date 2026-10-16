# Amplify release: 16 October 2026

This is a separate deployment copy of the working demo. Application source and features are retained; Next.js is pinned to the maintained 15.5.28 line because Amplify's managed Next SSR documentation lists versions through 15. The original local Next 16 checkout remains unchanged.

## AWS console setup

1. Connect a private GitHub repository containing this directory at its root. Amplify SSR does not support zip/manual deployment. Use Sydney (ap-southeast-2).
2. Use the committed amplify.yml. Node 22 runs npm ci, the runtime configuration helper, the frontend tests and the Next production build. Build artifacts: .next.
3. Set the required build variables ES_URL, KIBANA_URL, ES_API_KEY and BEDROCK_INFERENCE_ID using the existing local configuration. Also set AGENT_ID, OPENAUSTRALIA_KEY, RERANK_INFERENCE_ID and configured Workflow IDs. Never set NEXT_PUBLIC_ES_API_KEY or commit an env file.
4. The helper creates .env.production inside the cloud build only, from an explicit allowlist. AWS deployment artifacts may contain server secrets: restrict IAM/artifact access. The browser receives no secret values. For a production rollout, use a server execution role and Secrets Manager instead.
5. Leave EMAIL_CONNECTOR_ID unset until email delivery is configured and authorized. Do not enable the reminder schedule during hosting deployment.
6. After Amplify assigns its public HTTPS URL, set SITE_URL to that origin and rebuild. Test health, name lookup, both Alex Antic recommended titles, quoting, sharing metadata/PNG and saved quote access control.

## Scope

Elastic data stays in the existing cluster. The local historical backfill is not deployed or scheduled here. Missing local coverage metadata deliberately means incomplete coverage. Device-only collection management keys remain in the saving browser, scoped to this site's origin. A collection created on localhost is not automatically accessible on the new public origin.

Mail delivery and real-phone Contact Picker acceptance remain unverified. No hosting credentials, env secrets, raw archives or local evaluation files are included in this source tree.
