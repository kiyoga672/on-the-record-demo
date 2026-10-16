import {NextResponse} from 'next/server';
import {z} from 'zod';
import {exportFacts} from '@/lib/workflows';
import {errorResponse,sameOrigin,rateLimit} from '@/lib/http';
export const dynamic='force-dynamic';
export const maxDuration=300;
export async function POST(req:Request){try{sameOrigin(req);rateLimit('export',3);return NextResponse.json(await exportFacts(z.object({speaker_id:z.string().regex(/^\d+$/),topic:z.string().trim().min(2).max(160)}).parse(await req.json())));}catch(e){return errorResponse(e);}}
