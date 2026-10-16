import {NextResponse} from 'next/server';
import {topics,AppError} from '@/lib/elastic';
import {errorResponse} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET(req:Request){try{const id=new URL(req.url).searchParams.get('speaker_id')??'';if(!/^\d+$/.test(id))throw new AppError('Invalid speaker.',400);return NextResponse.json({topics:await topics(id)});}catch(e){return errorResponse(e);}}
