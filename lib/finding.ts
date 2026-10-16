import 'server-only';
import {member,timeline} from './elastic';
import type {Member,Timeline} from './types';
const findings=new Map<string,{until:number;value:Promise<{member:Member;result:Timeline}>}>();
// One shared, bounded, read-only result for SSR, metadata and OG. No alternate retrieval.
export function finding(id:string,topic:string){
 const key=JSON.stringify([id,topic]);const hit=findings.get(key);if(hit&&hit.until>Date.now())return hit.value;
 if(findings.size>=100)findings.delete(findings.keys().next().value!);
 const value=(async()=>{const m=await member(id);return {member:m,result:await timeline({speaker_id:id,speaker_name:m.name,topic})};})();
 findings.set(key,{until:Date.now()+300000,value});
 const remove=()=>{if(findings.get(key)?.value===value)findings.delete(key);};
 value.then(v=>{if(v.result.status==='verification_failed')remove();},remove);return value;
}
