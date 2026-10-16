import {NextResponse} from 'next/server';
import {members} from '@/lib/elastic';
import {errorResponse} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET(req:Request){try{const q=new URL(req.url).searchParams.get('q')??'';return NextResponse.json({members:await members(q.slice(0,100))});}catch(e){return errorResponse(e);}}
