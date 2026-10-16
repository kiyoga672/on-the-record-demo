import {NextResponse} from 'next/server';
import {emailSchema,managementHash,savedQuotes,removeSaved} from '@/lib/saved';
import {errorResponse,sameOrigin,rateLimit} from '@/lib/http';
export const dynamic='force-dynamic';
async function read(req:Request,email:unknown){const token=managementHash(req);rateLimit('saved:'+token,30);return NextResponse.json(await savedQuotes(emailSchema.parse(email),token),{headers:{'Cache-Control':'no-store'}});}
export async function GET(req:Request){try{return await read(req,new URL(req.url).searchParams.get('email'));}catch(e){return errorResponse(e);}}
// The UI uses POST to avoid putting personal email addresses in URLs/history.
export async function POST(req:Request){try{sameOrigin(req);return await read(req,(await req.json()).email);}catch(e){return errorResponse(e);}}
export async function DELETE(req:Request){try{sameOrigin(req);const token=managementHash(req);rateLimit('remove:'+token,4);return NextResponse.json(await removeSaved(emailSchema.parse((await req.json()).email),token),{headers:{'Cache-Control':'no-store'}});}catch(e){return errorResponse(e);}}
