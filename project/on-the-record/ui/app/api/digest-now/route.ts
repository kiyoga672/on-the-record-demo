import {NextResponse} from 'next/server';
import {emailSchema,managementHash,digestNow} from '@/lib/saved';
import {errorResponse,sameOrigin,rateLimit} from '@/lib/http';
export const dynamic='force-dynamic';
export async function POST(req:Request){try{sameOrigin(req);const token=managementHash(req);rateLimit('digest:'+token,3);return NextResponse.json(await digestNow(emailSchema.parse((await req.json()).email),token),{headers:{'Cache-Control':'no-store'}});}catch(e){return errorResponse(e);}}
