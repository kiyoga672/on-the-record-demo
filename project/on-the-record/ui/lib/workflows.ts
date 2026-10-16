import 'server-only';
import {createHash} from 'node:crypto';
import {elastic,AppError,verifyItems,member,retrievedCandidates,candidateContext} from './elastic';
import {ATTRIBUTION} from './types';
export async function runWorkflow(name:string,inputs:Record<string,string>){
 const id=process.env[name.toUpperCase()+'_WORKFLOW_ID'];if(!id)throw new AppError('This workflow is not configured yet.');
 const r=await elastic('kibana',`/api/workflows/workflow/${encodeURIComponent(id)}/run`,{inputs});
 const executionId=r.workflowExecutionId??r.executionId??r.id;
 if(typeof executionId!=='string')throw new AppError('Workflow did not return an execution ID.');
 for(let i=0;i<100;i++){
  const state=await elastic('kibana',`/api/workflows/executions/${encodeURIComponent(executionId)}`);
  if(['completed','success'].includes(state.status))return {executionId,state};
  if(['failed','cancelled','canceled'].includes(state.status))throw new AppError(`Workflow ${state.status}. Please retry.`);
  await new Promise(r=>setTimeout(r,1500));
 }
 throw new AppError('Workflow is still running. Check Kibana Workflows for its execution status.');
}
export async function follow(input:{email:string;speaker_id:string;topic:string}){
 const m=await member(input.speaker_id);
 const watch_id=createHash('sha256').update([input.email.toLowerCase(),input.speaker_id,input.topic.toLowerCase()].join('|')).digest('hex');
 const r=await runWorkflow('follow_topic',{...input,email:input.email.toLowerCase(),speaker_name:m.name,watch_id,created_at:new Date().toISOString()});
 return {execution_id:r.executionId,status:'completed',message:'Watch saved. Email delivery will begin when the daily digest is configured.'};
}
export async function exportFacts(input:{speaker_id:string;topic:string}){
 const m=await member(input.speaker_id);
 const candidates=candidateContext(await retrievedCandidates(m.person_id,input.topic),input.topic);
 const {executionId,state}=await runWorkflow('export_factsheet',{...input,speaker_name:m.name,candidates:JSON.stringify(candidates)});
 // Workflow execution stores step contexts. Find only the named agent step's structured output.
 function find(value:any):any{
  if(!value||typeof value!=='object')return null;
  if(value.structured_output?.items)return value.structured_output;
  if(value.output?.structured_output?.items)return value.output.structured_output;
  for(const v of Object.values(value)){const found=find(v);if(found)return found;}
  return null;
 }
 let data=find(state);
 if(!data){
  const step=state.stepExecutions?.find((s:any)=>s.stepId==='select_quotes'&&s.status==='completed');
  if(step){
   const detail=await elastic('kibana',`/api/workflows/executions/${encodeURIComponent(executionId)}/step/${encodeURIComponent(step.id)}`);
   data=find(detail);
  }
 }
 if(!data||!Array.isArray(data.items)||data.items.length>8)throw new AppError('Workflow output is unavailable or invalid.');
 const items=await verifyItems(data.items.filter((i:any)=>typeof i.speech_id==='string'&&typeof i.quote==='string'),m.person_id);
 if(!items.length)throw new AppError('The workflow returned no verifiable quotes. No fact sheet was generated.',422);
 const markdown=`# ${m.name} — ${input.topic}\n\nVerified excerpts from the currently indexed material. Index coverage is incomplete.\n\n`+
 items.map(i=>`> ${i.quote}\n\n[${i.date.slice(0,10)}, ${i.house}](${i.url})\n`).join('\n')+`\n${ATTRIBUTION}\n`;
 return {execution_id:executionId,status:'completed',markdown,quotes_verified:items.length};
}
