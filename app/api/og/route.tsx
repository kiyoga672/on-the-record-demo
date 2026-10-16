import {ImageResponse} from 'next/og';
import {finding} from '@/lib/finding';
import {formatDate,absence} from '@/lib/emailTemplate';
import {ATTRIBUTION} from '@/lib/types';
import {errorResponse} from '@/lib/http';
import {AppError} from '@/lib/elastic';
export const revalidate=300;
export async function GET(req:Request){try{
 const params=new URL(req.url).searchParams,id=params.get('speaker_id')??'',topic=params.get('topic')?.trim()??'';
 if(!/^\d+$/.test(id)||topic.length<2||topic.length>160)throw new AppError('Invalid finding parameters.',400);
 const {member:m,result}=await finding(id,topic);const q=result.items[0];
 if(result.status==='verification_failed')throw new AppError('Finding could not be verified.',503);
 return new ImageResponse(<div style={{display:'flex',flexDirection:'column',width:'100%',height:'100%',background:'#f7f6f1',color:'#18372d',padding:'46px 60px',fontFamily:'sans-serif'}}><div style={{display:'flex',fontSize:22,letterSpacing:3}}>ON THE RECORD · VERIFIED HANSARD</div><div style={{display:'flex',fontSize:42,fontWeight:700,marginTop:18}}>{m.name}</div><div style={{display:'flex',fontSize:22,marginTop:6}}>{m.party} · {m.electorate||m.state} · On {topic}</div><div style={{display:'flex',fontSize:q?30:26,lineHeight:1.32,marginTop:28,flexGrow:1}}>{q?`“${q.quote}”`:absence(m.name,topic,result.coverage.complete)}</div><div style={{display:'flex',fontSize:21,marginTop:14}}>{q?`${formatDate(q.date)}, ${q.house}`:'Current indexed collection'}</div><div style={{display:'flex',fontSize:16,marginTop:18,borderTop:'1px solid #bac8be',paddingTop:14}}>{ATTRIBUTION}</div></div>,{width:1200,height:630,headers:{'Cache-Control':'public, max-age=300'}});
 }catch(e){return errorResponse(e);}}
