import {NextResponse} from 'next/server';
import {coverage} from '@/lib/elastic';
import {errorResponse} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET(){try{return NextResponse.json({ready:true,coverage:await coverage()});}catch(e){return errorResponse(e);}}
