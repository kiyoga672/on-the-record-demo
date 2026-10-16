import type {Speech, Quote} from './types';
export async function collectVerifiedQuotes(items:{speech_id:string;quote:string}[],validate:(item:{speech_id:string;quote:string})=>Promise<Quote|null>){
 const out:Quote[]=[],seen=new Set<string>();
 for(const candidate of items){
  if(seen.has(candidate.speech_id))continue;
  const verified=await validate(candidate);
  // A rejected excerpt must not consume the speech's slot: a later exact
  // excerpt from the same source may still be valid.
  if(verified){seen.add(candidate.speech_id);out.push(verified);}
 }
 return out.sort((a,b)=>b.date.localeCompare(a.date));
}
export function topicVocabulary(topic:string){
 const synonyms:Record<string,string>={housing:'housing house homes rent mortgage homeless equity',health:'health healthcare hospital medical medicare',education:'education school university learning student',energy:'energy electricity gas power renewable',hecs:'HECS HELP student debt indexation',climate:'climate emissions carbon warming',defence:'defence defense military armed forces',migration:'migration immigration migrant refugees',tax:'tax taxation taxes',transport:'transport rail roads railway transit'};
 const value=synonyms[topic.trim().toLowerCase()];
 return {query:value??topic,operator:value?'or' as const:'and' as const};
}
export function verifyCandidate(s:Speech, speakerId:string, quote:string):Quote|null {
  if(s.speaker_id!==speakerId || !quote.trim() || quote!==quote.trim() || quote.split(/\s+/).length>60) return null;
  if(s.date.slice(0,10)<'2025-01-01' || !s.text.includes(quote)) return null;
  let url:URL; try {url=new URL(s.url);} catch{return null;}
  if(url.protocol!=='https:' || url.hostname!=='www.openaustralia.org.au' || !['/debates/','/senate/'].includes(url.pathname) || !url.searchParams.get('id')) return null;
  if((s.house==='Senate')!==(url.pathname==='/senate/') || !['House','Senate'].includes(s.house)) return null;
  const {text,...metadata}=s;
  return {...metadata,quote,verified:true};
}
export function attentionScore(share:number,shares:number[]):number|null {
  if(shares.length<2 || shares.some(x=>!Number.isFinite(x)||x<0)) return null;
  const sorted=[...shares].sort((a,b)=>a-b), i=Math.floor(sorted.length/2);
  const median=sorted.length%2 ? sorted[i] : (sorted[i-1]+sorted[i])/2;
  return median>0 ? Math.min(100,Math.max(0,Math.round(50*share/median))) : null;
}
