import 'server-only';
import {createHash,timingSafeEqual} from 'node:crypto';
import {z} from 'zod';
import {elastic,AppError,verifyItems,member} from './elastic';
import {runWorkflow} from './workflows';

export const emailSchema=z.string().trim().email().max(254).transform(v=>v.toLowerCase());
export const saveSchema=z.object({email:emailSchema,speaker_id:z.string().regex(/^\d+$/),speech_id:z.string().min(1).max(250),topic:z.string().trim().min(2).max(160),quote:z.string().min(1).max(2000),url:z.string().url().max(1000),date:z.string().max(40),house:z.string().max(40),remind_on:z.string().regex(/^\d{4}-\d{2}-\d{2}$/),monthly:z.boolean()});
export const hash=(v:string)=>createHash('sha256').update(v).digest('hex');
export function managementHash(req:Request){const token=req.headers.get('authorization')?.match(/^Bearer ([a-f0-9]{64})$/i)?.[1];if(!token)throw new AppError('Use the browser where you saved your quotes to manage them.',401);return hash(token);}
function matches(a:string,b:string){return /^[a-f0-9]{64}$/.test(a)&&timingSafeEqual(Buffer.from(a,'hex'),Buffer.from(b,'hex'));}
async function owner(email:string){const r=await elastic('es','/saved_quotes/_search',{size:1,query:{ids:{values:['owner:'+hash(email)]}}});return r.hits.hits[0]?._source;}
export async function requireOwner(email:string,management_hash:string){const existing=await owner(email);if(!existing||!matches(existing.management_hash??'',management_hash))throw new AppError('These saved quotes belong to another browser, or no saved collection exists here.',403);}
async function claimOwner(email:string,management_hash:string){
 const current=await owner(email);if(current){await requireOwner(email,management_hash);return;}
 // Create-only ownership prevents concurrent first saves from claiming one email
 // with two different tokens. Remove all deletes this marker with the quotes.
 try{await elastic('es',`/saved_quotes/_create/${encodeURIComponent('owner:'+hash(email))}?refresh=wait_for`,{email,management_hash,record_kind:'ownership',created_at:new Date().toISOString()},'PUT');}
 catch{await requireOwner(email,management_hash);}
}
export async function saveQuote(input:z.infer<typeof saveSchema>,management_hash:string){
 if(!process.env.SAVE_QUOTE_WORKFLOW_ID)throw new AppError('Saved quote storage is not configured yet.',503);
 const reminder=new Date(input.remind_on+'T23:59:59Z');if(!Number.isFinite(reminder.getTime())||reminder.toISOString().slice(0,10)!==input.remind_on||reminder.getTime()<Date.now())throw new AppError('Choose today or a future reminder date.',400);
 const verified=(await verifyItems([{speech_id:input.speech_id,quote:input.quote}],input.speaker_id))[0];
 if(!verified||verified.url!==input.url||verified.date!==input.date||verified.house!==input.house)throw new AppError('The submitted quote or source details do not match Hansard.',422);
 const person=await member(input.speaker_id);await claimOwner(input.email,management_hash);
 const quote_hash=hash(input.speaker_id+verified.quote),document_id=hash(input.email+quote_hash);
 const r=await runWorkflow('save_quote',{email:input.email,speaker_id:person.person_id,speaker_name:person.name,party:person.party,topic:input.topic,quote:verified.quote,speech_id:verified.speech_id,date:verified.date,house:verified.house,url:verified.url,remind_on:input.remind_on+'T00:00:00Z',monthly:input.monthly,quote_hash,document_id,management_hash} as unknown as Record<string,string>);
 const stored=await elastic('es','/saved_quotes/_search',{size:1,query:{ids:{values:[document_id]}}});
 const doc=stored.hits.hits[0]?._source;
 if(!doc||doc.email!==input.email||doc.management_hash!==management_hash||doc.quote!==verified.quote||doc.url!==verified.url)throw new AppError('The workflow did not confirm a verified saved quote. Nothing was reported as saved.',422);
 return {status:'completed',execution_id:r.executionId,message:'Quote saved. Manage reminders from Saved quotes in this browser.'};
}
export async function savedQuotes(email:string,management_hash:string){await requireOwner(email,management_hash);const r=await elastic('es','/saved_quotes/_search',{size:500,query:{bool:{filter:[{term:{email}},{term:{management_hash}},{exists:{field:'quote_hash'}}]}},sort:[{date:'desc'}]});return {items:r.hits.hits.map((h:any)=>({id:h._id,...h._source,management_hash:undefined,email:undefined})),total:r.hits.total.value};}
export async function removeSaved(email:string,management_hash:string){
 await requireOwner(email,management_hash);
 const existing=await owner(email);
 if(existing?.delivery_pending===true)throw new AppError('A digest is currently being delivered. Please remove your saved quotes after it finishes.',409);
 // Delete the ownership marker as well, so removing a collection leaves no
 // retained email address. A later save must claim ownership again.
 const r=await elastic('es','/saved_quotes/_delete_by_query?refresh=true',{query:{bool:{filter:[{term:{email}},{term:{management_hash}}]}}});
 if(r.failures?.length||r.version_conflicts)throw new AppError('Some saved records could not be removed. Please retry.',409);
 return {deleted:r.deleted};
}
export async function digestNow(email:string,management_hash:string){
 await requireOwner(email,management_hash);
 const wid=process.env.REMINDER_DIGEST_WORKFLOW_ID;
 if(!process.env.EMAIL_CONNECTOR_ID||!wid)throw new AppError('Reminder email delivery is not configured yet. Your saved quotes are retained.',501);
 const workflow=await elastic('kibana',`/api/workflows/workflow/${encodeURIComponent(wid)}`);
 if(workflow.enabled!==true)throw new AppError('Reminder delivery has not been enabled and verified yet. No email was sent.',501);
 const {executionId,state}=await runWorkflow('reminder_digest',{email,management_hash,as_of:new Date().toISOString(),send_now:true} as unknown as Record<string,string>);
 const deliveries=state.stepExecutions?.filter((s:any)=>s.stepId==='send_digest'&&s.status==='completed')??[];
 for(const step of deliveries){
  const detail=await elastic('kibana',`/api/workflows/executions/${encodeURIComponent(executionId)}/step/${encodeURIComponent(step.id)}`);
  const output=detail.output??detail.stepExecution?.output;
  if(output?.status!=='ok')throw new AppError('The email service did not confirm delivery. Check the workflow before retrying.');
 }
 return {execution_id:executionId,message:deliveries.length?'The email service accepted your digest.':'No pending quotes were sent. Any delivery already in progress must finish first.'};
}
