import {NextResponse} from 'next/server';
import {z} from 'zod';
import {follow} from '@/lib/workflows';
import {errorResponse,sameOrigin,rateLimit} from '@/lib/http';
export const dynamic='force-dynamic';
export async function POST(req:Request){try{sameOrigin(req);rateLimit('follow',4);const input=z.object({email:z.string().email().max(254),speaker_id:z.string().regex(/^\d+$/),topic:z.string().trim().min(2).max(160)}).parse(await req.json());return NextResponse.json(await follow(input));}catch(e){return errorResponse(e);}}
