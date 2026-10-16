import {NextResponse} from 'next/server';
import {ZodError} from 'zod';
import {AppError} from './elastic';
const buckets=new Map<string,{count:number;until:number}>();
export function rateLimit(key:string,max=12){
 const now=Date.now();if(buckets.size>1000)for(const [k,v]of buckets)if(v.until<now)buckets.delete(k);
 const v=buckets.get(key);if(!v||v.until<now){buckets.set(key,{count:1,until:now+60000});return;}
 if(++v.count>max)throw new AppError('Too many requests. Please wait a minute.',429);
}
export function sameOrigin(req:Request){
 const origin=req.headers.get('origin');if(!origin)return;
 // Next.js may construct req.url with its internal hostname; compare the browser's
 // Origin to the actual Host header, not that internal URL.
 let parsed:URL;try{parsed=new URL(origin);}catch{throw new AppError('Request origin is not allowed.',403);}
 const host=req.headers.get('host')??new URL(req.url).host;
 if(parsed.host!==host||!['http:','https:'].includes(parsed.protocol))throw new AppError('Request origin is not allowed.',403);
}
export function errorResponse(e:unknown){
 const status=e instanceof ZodError?400:e instanceof AppError?e.status:503;
 return NextResponse.json({error:e instanceof ZodError?'Please check the submitted fields.':e instanceof AppError?e.message:'The service is temporarily unavailable. Please retry.'},{status,headers:{'Cache-Control':'no-store'}});
}
