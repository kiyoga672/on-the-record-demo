// Amplify build variables are not automatically available to Next SSR.
// Write an explicit allowlist without ever printing secret values.
import {writeFileSync} from 'node:fs';
const required=['ES_URL','KIBANA_URL','ES_API_KEY','BEDROCK_INFERENCE_ID'];
const optional=['OPENAUSTRALIA_KEY','AGENT_ID','RERANK_INFERENCE_ID',
 'FIND_MY_MP_WORKFLOW_ID','FOLLOW_TOPIC_WORKFLOW_ID','EXPORT_FACTSHEET_WORKFLOW_ID',
 'SAVE_QUOTE_WORKFLOW_ID','REMINDER_DIGEST_WORKFLOW_ID','EMAIL_CONNECTOR_ID',
 'SITE_URL','NEXT_PUBLIC_REMINDER_DEFAULT'];
const missing=required.filter(k=>!process.env[k]?.trim());
if(missing.length)throw new Error(`Configure Amplify build variables: ${missing.join(', ')}`);
const lines=[...required,...optional].filter(k=>process.env[k]?.trim()).map(k=>`${k}=${JSON.stringify(process.env[k])}`);
writeFileSync('.env.production',lines.join('\n')+'\n',{mode:0o600});
console.log('Prepared allowlisted SSR runtime configuration; values hidden.');
