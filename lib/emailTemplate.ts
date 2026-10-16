import {ATTRIBUTION,type Member,type Quote,type Timeline} from './types';
export const formatDate=(date:string)=>new Date(date).toLocaleDateString('en-AU',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
export const newest=(items:Quote[])=>[...items].sort((a,b)=>b.date.localeCompare(a.date)).slice(0,3);
export function absence(name:string,topic:string,complete:boolean){return complete?`The Hansard record shows no statements by ${name} on ${topic} since 1 January 2025.`:`No verified statements by ${name} on ${topic} were found in the currently indexed material. Coverage is incomplete; this does not establish absence from Hansard.`;}
export function emailTemplate(m:Member,topic:string,result:Timeline){
 const subject=`Question regarding your statements on ${topic} in Parliament`;
 const record=result.items.length?`I am a constituent in ${m.electorate||m.state||'[your electorate or state]'}. I have been reading the Hansard record of your statements on ${topic}. For reference:\n\n`+newest(result.items).map(q=>`- ${formatDate(q.date)}, ${q.house}: "${q.quote}"\n  ${q.url}`).join('\n') :absence('you',topic,result.coverage.complete);
 const body=`Dear ${m.name},\n\n${record}\n\n[Write your question or comment here.]\n\nI would appreciate a reply.\n\nKind regards,\n[Your name]\n[Your suburb and postcode]\n\n${ATTRIBUTION}`;
 return {subject,body,text:`Subject: ${subject}\n\n${body}`};
}
export function emailLink(email:string,subject:string,body:string){return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;}
