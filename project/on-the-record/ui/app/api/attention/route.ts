import {NextResponse} from 'next/server';
import {attention,inputSchema,member} from '@/lib/elastic';
import {errorResponse} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET(req:Request){try{const s=new URL(req.url).searchParams;const input=inputSchema.parse({speaker_id:s.get('speaker_id'),speaker_name:'lookup',topic:s.get('topic')});const m=await member(input.speaker_id);return NextResponse.json(await attention(m.person_id,input.topic,m.house));}catch(e){return errorResponse(e);}}
