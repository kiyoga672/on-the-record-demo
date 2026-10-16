import {ATTRIBUTION,type Member,type Timeline} from './types';
import {absence,formatDate,newest} from './emailTemplate';
export function petitionTemplate(m:Member,topic:string,result:Timeline){
 const title=`Ask ${m.name} to ${result.items.length?'address':'speak on'} ${topic} in Parliament`;
 const role=m.house==='Senate'?`Senator for ${m.state||'[state]'}`:`Member for ${m.electorate||'[electorate]'}`;
 const record=result.items.length?`The official Hansard record shows the following statements by ${m.name} on ${topic}:\n\n`+newest(result.items).map(q=>`- ${formatDate(q.date)}, ${q.house}: "${q.quote}" (${q.url})`).join('\n'):absence(m.name,topic,result.coverage.complete);
 const body=`To: ${m.name}, ${role}\n\n${record}\n\n[Explain here what you are asking for and why.]\n\nWe, the undersigned, ask ${m.name} to respond publicly to this request.\n\n${ATTRIBUTION}`;
 return {title,body};
}
