import {NextResponse} from 'next/server';
import {saveSchema,saveQuote,managementHash} from '@/lib/saved';
import {errorResponse,sameOrigin,rateLimit} from '@/lib/http';
export const dynamic='force-dynamic';
export async function POST(req:Request){try{sameOrigin(req);const token=managementHash(req);rateLimit('save:'+token,8);return NextResponse.json(await saveQuote(saveSchema.parse(await req.json()),token),{headers:{'Cache-Control':'no-store'}});}catch(e){return errorResponse(e);}}
