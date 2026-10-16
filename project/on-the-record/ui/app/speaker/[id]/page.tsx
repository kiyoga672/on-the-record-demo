import Link from 'next/link';
import {member,topics} from '@/lib/elastic';
import Speaker from '@/components/Speaker';
import type {Metadata} from 'next';
import {headers} from 'next/headers';
import {finding} from '@/lib/finding';
import {formatDate,absence} from '@/lib/emailTemplate';
import {findingPath} from '@/lib/sharing';
type Props={params:Promise<{id:string}>;searchParams:Promise<{topic?:string|string[]}>};
const validTopic=(x:string|string[]|undefined)=>typeof x==='string'&&x.trim().length>=2&&x.trim().length<=160?x.trim():'';
export const dynamic='force-dynamic';
export async function generateMetadata({params,searchParams}:Props):Promise<Metadata>{
 const {id}=await params,topic=validTopic((await searchParams).topic);
 if(!/^\d+$/.test(id))return {title:'Speaker not found — On the Record'};
 try{const m=await member(id),title=`${m.name}${topic?` on ${topic}`:''} — On the Record`;
 const h=await headers(),host=h.get('host')??'127.0.0.1:3000';
 const origin=process.env.SITE_URL||`${/^(localhost|127\.0\.0\.1)(:|$)/.test(host)?'http':'https'}://${host}`;
 let description=`Explore verified Hansard statements by ${m.name}, ${m.party}, ${m.electorate||m.state}.`;
 if(topic){try{const {result}=await finding(id,topic),q=result.items[0];description=q?`${q.quote.slice(0,180)} [${formatDate(q.date)}, ${q.house}]`:result.status==='verification_failed'?'This finding could not be verified. Please retry.':absence(m.name,topic,result.coverage.complete);}catch{description='The records service is temporarily unavailable. Please retry.';}}
 const image=`${origin}/api/og?${new URLSearchParams({speaker_id:id,topic})}`;
 return {title,description,alternates:{canonical:origin+(topic?findingPath(id,topic):`/speaker/${id}`)},openGraph:{title,description,...(topic?{images:[{url:image,width:1200,height:630}]}:{})},twitter:{card:'summary_large_image',title,description,...(topic?{images:[image]}:{})}};
 }catch{return {title:'On the Record',description:'The records service is temporarily unavailable.'};}
}
export default async function Page({params,searchParams}:Props){
 const {id}=await params;
 if(!/^\d+$/.test(id))return <main><h1>Speaker not found</h1><Link href="/">Back to search</Link></main>;
 try{const m=await member(id),topic=validTopic((await searchParams).topic);let titles=[];try{titles=await topics(id);}catch{}let initial=null;try{if(topic)initial=(await finding(id,topic)).result;}catch{}return <Speaker key={id} member={m} topics={titles} initialTopic={topic} initialResult={initial}/>;}
 catch{return <main><h1>Unable to load this speaker</h1><p>The records service may be unavailable.</p><Link href="/">Back to search</Link></main>;}
}
