import {NextResponse} from 'next/server';
import {member,AppError} from '@/lib/elastic';
import {errorResponse,rateLimit} from '@/lib/http';
const cache=new Map<string,{name:string;email:string|null;contact_url:string}>();
export async function GET(req:Request){try{
 rateLimit('contact',40);const id=new URL(req.url).searchParams.get('speaker_id')??'';
 if(!/^\d+$/.test(id))throw new AppError('Invalid speaker ID.',400);
 if(cache.has(id))return NextResponse.json(cache.get(id));
 const m=await member(id);let email:string|null=null;
 if(process.env.OPENAUSTRALIA_KEY){try{
 const u=new URL(`https://www.openaustralia.org.au/api/${m.house==='Senate'?'getSenator':'getRepresentative'}`);u.searchParams.set('id',id);u.searchParams.set('output','js');u.searchParams.set('key',process.env.OPENAUSTRALIA_KEY);
 const r=await fetch(u,{signal:AbortSignal.timeout(10000),cache:'no-store'});
 if(r.ok){const data=await r.json();const row=Array.isArray(data)?data[0]:data;
 for(const value of [row?.email,row?.office_email,row?.contact_email])if(typeof value==='string'&&/^[^\s@]+@(?:[a-z0-9-]+\.)*aph\.gov\.au$/i.test(value))email=value;}
 }catch{}}
 const result={name:m.name,email,contact_url:`https://www.aph.gov.au/Senators_and_Members/Parliamentarian_Search_Results?q=${encodeURIComponent(m.name)}`};cache.set(id,result);return NextResponse.json(result);
 }catch(e){return errorResponse(e);}}
