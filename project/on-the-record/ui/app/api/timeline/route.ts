import {NextResponse} from 'next/server';
import {inputSchema} from '@/lib/elastic';
import {finding} from '@/lib/finding';
import {errorResponse,rateLimit,sameOrigin} from '@/lib/http';
export const dynamic='force-dynamic';
export const maxDuration=300;
export async function POST(req:Request){try{sameOrigin(req);rateLimit('timeline',8);const input=inputSchema.parse(await req.json());return NextResponse.json((await finding(input.speaker_id,input.topic)).result);}catch(e){return errorResponse(e);}}
