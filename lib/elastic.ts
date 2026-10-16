import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {z} from 'zod';
import type {Member,Speech,Timeline} from './types';
import {ATTRIBUTION} from './types';
import {verifyCandidate,attentionScore,topicVocabulary,collectVerifiedQuotes} from './verification';
import {topicEvidenceQuery} from './retrievalQuery';

export class AppError extends Error { constructor(message:string,public status=503){super(message);} }
function env(key:string){const s=process.env[key]?.trim();if(!s)throw new AppError(`Server configuration missing: ${key}`);return s;}
export async function elastic(service:'es'|'kibana', route:string, body?:unknown, method?:string){
 const response=await fetch(env(service==='es'?'ES_URL':'KIBANA_URL').replace(/\/$/,'')+route,{
  method:method??(body?'POST':'GET'),headers:{Authorization:`ApiKey ${env('ES_API_KEY')}`,'kbn-xsrf':'true','Content-Type':'application/json'},
  body:body?JSON.stringify(body):undefined,cache:'no-store',signal:AbortSignal.timeout(180000)});
 if(!response.ok)throw new AppError(`${service==='es'?'Search':'Agent'} service returned ${response.status}. Please retry.`);
 return response.json();
}
export const inputSchema=z.object({speaker_id:z.string().regex(/^\d+$/),speaker_name:z.string().min(1).max(160),topic:z.string().trim().min(2).max(160)});
export async function members(q=''):Promise<Member[]>{
 const r=await elastic('es','/members/_search',{size:250,query:q?{multi_match:{query:q,fields:['name.text^3','electorate','state'],type:'bool_prefix'}}:{match_all:{}},sort:[{name:'asc'}]});
 return r.hits.hits.map((h:{_source:Member})=>h._source);
}
export async function member(id:string):Promise<Member>{
 const r=await elastic('es','/members/_search',{size:1,query:{term:{person_id:id}}});
 if(!r.hits.hits.length)throw new AppError('Speaker not found.',404);return r.hits.hits[0]._source;
}
export async function esql(query:string,params:Record<string,string>={}){
 const r=await elastic('es','/_query',{query,params:Object.entries(params).map(([k,v])=>({[k]:v}))});
 return r.values.map((row:unknown[])=>Object.fromEntries(r.columns.map((c:{name:string},i:number)=>[c.name,row[i]])));
}
export async function topics(id:string){
 return esql('FROM hansard | WHERE speaker_id == ?speaker_id AND date >= TO_DATETIME("2025-01-01T00:00:00Z") | STATS speeches=COUNT(*) BY debate_title.kw | SORT speeches DESC | LIMIT 10',{speaker_id:id});
}
export async function coverage(){
 const r=await elastic('es','/hansard/_search',{size:0,aggs:{first:{min:{field:'date'}},last:{max:{field:'date'}}},track_total_hits:true});
 let complete=false;
 try{const c=JSON.parse(await readFile(path.resolve(process.cwd(),'../.local/coverage.json'),'utf8'));complete=c.complete===true;}catch{}
 return {complete,from:r.aggregations.first.value_as_string?.slice(0,10)??'',to:r.aggregations.last.value_as_string?.slice(0,10)??'',documents:r.hits.total.value};
}
export function hybridQuery(id:string,topic:string){
 const filter=[{term:{speaker_id:id}},{range:{date:{gte:'2025-01-01'}}}];
 return {size:8,retriever:{text_similarity_reranker:{retriever:{rrf:{retrievers:[
  {standard:{query:{bool:{must:[topicEvidenceQuery(topic)],filter}}}},
  {standard:{query:{bool:{must:[{semantic:{field:'semantic_body',query:topic}}],filter}}}}
 ],rank_window_size:40,rank_constant:60}},field:'text',inference_id:process.env.RERANK_INFERENCE_ID??'.rerank-v1-elasticsearch',inference_text:topic,rank_window_size:20}},
 _source:['speech_id','speaker_id','speaker_name','date','house','party','debate_title','text','url']};
}
export function candidateContext(sources:Speech[],topic:string){
 return sources.slice(0,4).map(s=>{const pos=Math.max(0,s.text.toLowerCase().indexOf(topic.toLowerCase())-250);return {...s,text:s.text.slice(pos,pos+2200)};});
}
export async function retrievedCandidates(id:string,topic:string):Promise<Speech[]>{
 const search=await elastic('es','/hansard/_search',hybridQuery(id,topic));
 const docs:Speech[]=search.hits.hits.map((h:any)=>h._source);
 if(!docs.length)return [];
 // Semantic similarity alone can make fabricated/unknown topics look answerable.
 // Accept explicit body vocabulary OR a source debate-heading phrase. Chips
 // come from those headings and must remain searchable even without body repeats.
 const evidence=await elastic('es','/hansard/_search',{size:8,_source:['speech_id'],query:{bool:{filter:[{term:{speaker_id:id}},{terms:{speech_id:docs.map(d=>d.speech_id)}}],must:[topicEvidenceQuery(topic)]}}});
 const ids=new Set(evidence.hits.hits.map((h:any)=>h._source.speech_id));
 return docs.filter(d=>ids.has(d.speech_id));
}
export function parseAgent(r:Record<string,any>){
 const message=r.response?.message??r.message;
 if(typeof message!=='string')throw new AppError('Agent returned an unsupported response.');
 const cleaned=message.trim().replace(/^```(?:json)?\s*/,'').replace(/\s*```$/,'');
 const schema=z.object({items:z.array(z.object({speech_id:z.string().max(200),quote:z.string().max(2000)})).max(8)});
 try{return {items:schema.parse(JSON.parse(cleaned)).items,toolCalls:(r.steps??[]).filter((s:any)=>s.type==='tool_call').map((s:any)=>String(s.tool_id))};}
 catch{throw new AppError('Agent response could not be verified. Please retry.');}
}
async function converse(input:string){
 const response=await fetch(env('KIBANA_URL').replace(/\/$/,'')+'/api/agent_builder/converse/async',{
  method:'POST',headers:{Authorization:`ApiKey ${env('ES_API_KEY')}`,'kbn-xsrf':'true','Content-Type':'application/json'},
  body:JSON.stringify({agent_id:process.env.AGENT_ID??'on-the-record',inference_id:env('BEDROCK_INFERENCE_ID'),
   configuration_overrides:{tools:[{tool_ids:['verify_quote']}]},input}),signal:AbortSignal.timeout(120000),cache:'no-store'});
 if(!response.ok||!response.body)throw new AppError(`Agent service returned ${response.status}. Please retry.`);
 const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
 try{while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true}).replace(/\r\n/g,'\n');
  let end;while((end=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,end);buffer=buffer.slice(end+2);
   const event=block.split('\n').find(x=>x.startsWith('event:'))?.slice(6).trim();
   if(event==='round_complete'){const data=block.split('\n').filter(x=>x.startsWith('data:')).map(x=>x.slice(5).trim()).join('\n');const parsed=JSON.parse(data);const round=parsed.data?.round??parsed.round;
    if(!round)throw new AppError('Agent returned an incomplete round.');return round;}
   if(event==='error')throw new AppError('Agent execution failed. Please retry.');
  }
 }}finally{await reader.cancel().catch(()=>{});}
 throw new AppError('Agent stream ended before a verified response was available.');
}
export async function verifyItems(items:{speech_id:string;quote:string}[],id:string){
 return collectVerifiedQuotes(items,async candidate=>{
  const tool=await elastic('kibana','/api/agent_builder/tools/_execute',{tool_id:'verify_quote',tool_params:{speaker_id:id,quote:candidate.quote}});
  // A successful HTTP response may still contain a tool error: fail closed.
  if(JSON.stringify(tool).includes('"type":"error"'))return null;
  const r=await elastic('es','/hansard/_search',{size:1,query:{bool:{filter:[{term:{speech_id:candidate.speech_id}},{term:{speaker_id:id}}]}}});
  if(!r.hits.hits.length)return null;
  return verifyCandidate(r.hits.hits[0]._source as Speech,id,candidate.quote);
 });
}
export async function timeline(input:z.infer<typeof inputSchema>):Promise<Timeline>{
 const start=Date.now();const person=await member(input.speaker_id);
 const [candidates,cov]=await Promise.all([retrievedCandidates(person.person_id,input.topic),coverage()]);
 if(!candidates.length){
  return {status:cov.complete?'no_matches':'incomplete_coverage',items:[],
   message:cov.complete?`No recorded statements by ${person.name} on ${input.topic} in Hansard since 1 Jan 2025.`:
    `No verified matches for ${person.name} on ${input.topic} in the currently indexed material. Coverage is incomplete.`,
   attribution:ATTRIBUTION,tool_calls:[],latency_ms:Date.now()-start,coverage:cov};
 }
 const agent=await converse(JSON.stringify({task:'Choose at most two relevant continuous verbatim excerpts from these already-retrieved hybrid candidates. Do not search again. Call verify_quote sequentially, once for each chosen quote, passing speaker_id and quote explicitly as string arguments. If a tool call errors, do not retry the same quote. Return JSON only: {items:[{speech_id,quote}],attribution}. No follow/export calls. Do not add records outside candidates.',speaker_id:person.person_id,speaker_name:person.name,topic:input.topic,index_coverage:cov,candidates:candidateContext(candidates,input.topic)}));
 const parsed=parseAgent(agent);
 if(parsed.items.some(i=>!candidates.some((s:Speech)=>s.speech_id===i.speech_id)))throw new AppError('Agent selected a record outside the retrieved candidates.');
 const items=await verifyItems(parsed.items,person.person_id);
 const status=items.length?'verified':parsed.items.length?'verification_failed':cov.complete?'no_matches':'incomplete_coverage';
 const message=status==='verified'?'':status==='verification_failed'?'Matching speeches were retrieved, but the selected excerpts failed exact source checks. Please retry.':cov.complete?
 `No recorded statements by ${person.name} on ${input.topic} in Hansard since 1 Jan 2025.`:
 `No verified matches for ${person.name} on ${input.topic} in the currently indexed material. Coverage is incomplete.`;
 return {status,items,message,attribution:ATTRIBUTION,tool_calls:[...parsed.toolCalls,...items.map(()=> 'verify_quote (server)')],latency_ms:Date.now()-start,coverage:cov};
}
export async function attention(id:string,topic:string,house:string){
 const vocabulary=topicVocabulary(topic);const match=`(MATCH(text, ?topic, {"operator":"${vocabulary.operator}"}) OR MATCH_PHRASE(debate_title, ?heading))`;
 const [counts,monthly,cov]=await Promise.all([
 esql(`FROM hansard | WHERE house == ?house AND date >= TO_DATETIME("2025-01-01T00:00:00Z") | STATS total=COUNT(*), on_topic=COUNT(*) WHERE ${match} BY speaker_id | WHERE total >= 5 | EVAL share=TO_DOUBLE(on_topic)/TO_DOUBLE(total) | LIMIT 10000`,{house,topic:vocabulary.query,heading:topic}),
 esql(`FROM hansard | WHERE speaker_id == ?speaker_id AND date >= TO_DATETIME("2025-01-01T00:00:00Z") AND ${match} | STATS n=COUNT(*) BY month=DATE_TRUNC(1 month,date) | SORT month | LIMIT 1000`,{speaker_id:id,topic:vocabulary.query,heading:topic}),coverage()]);
 const own=counts.find((c:any)=>c.speaker_id===id);
 return {score:own&&cov.complete?attentionScore(own.share,counts.map((c:any)=>c.share)):null,total:own?.total??null,on_topic:own?.on_topic??null,eligible_speakers:counts.length,monthly,coverage:cov,
 reason:cov.complete?'A score requires at least five speeches and a nonzero chamber median.':'Chamber comparison is unavailable until index coverage is complete.'};
}
