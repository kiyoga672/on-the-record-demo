'use client';
import {useEffect,useState} from 'react';
import {ATTRIBUTION,type Member} from '@/lib/types';
import {emailLink} from '@/lib/emailTemplate';
import {findingPath,shareLinks} from '@/lib/sharing';
type ContactNavigator=Navigator&{contacts?:{select:(fields:string[],options:{multiple:boolean})=>Promise<{email?:string[];tel?:string[]}[]>}};
export default function ShareBar({member:m,topic}:{member:Member;topic:string}){
 const [url,setUrl]=useState(''),[native,setNative]=useState(false),[picker,setPicker]=useState(false),[open,setOpen]=useState(false),[notice,setNotice]=useState('');
 useEffect(()=>{setUrl(location.origin+findingPath(m.person_id,topic));setNative(typeof navigator.share==='function');setPicker('contacts' in navigator&&'ContactsManager' in window);},[m.person_id,topic]);
 useEffect(()=>{if(!notice)return;const t=setTimeout(()=>setNotice(''),2000);return()=>clearTimeout(t);},[notice]);
 const {text,links}=shareLinks(m.name,topic,url);
 const title=`${m.name} on ${topic} — On the Record`;
 const friends=`Thought you might want to see what ${m.name} has said in Parliament on ${topic} — verified Hansard quotes: ${url}\n\n${ATTRIBUTION}`;
 async function copy(){try{await navigator.clipboard.writeText(url);setNotice('Link copied');}catch{setNotice('Copy unavailable. Copy the address from your browser.');}}
 async function share(family=false){try{await navigator.share({title,text:family?friends:text,...(family?{}:{url})});}catch(e){if((e as Error).name!=='AbortError')setNotice('Sharing unavailable. Use Copy link.');}}
 async function contacts(){try{
 const selected=await (navigator as ContactNavigator).contacts!.select(['email','tel'],{multiple:true});
 const emails=selected.flatMap(x=>x.email??[]).filter(x=>/^[^\s@,;:?]+@[^\s@,;:?]+\.[^\s@,;:?]+$/.test(x));
 const phones=selected.flatMap(x=>x.tel??[]).map(x=>x.replace(/[^+\d]/g,'')).filter(Boolean);
 if(emails.length)location.href=emailLink(emails.map(encodeURIComponent).join(','),title,friends);
 else if(phones.length)location.href=`sms:${phones.join(',')}?body=${encodeURIComponent(friends)}`;
 else setNotice('No contacts selected');
 }catch{setNotice('No contacts selected');}}
 return <div className="share-section" aria-label="Share this finding"><div className="actions share-bar">{Object.entries(links).map(([name,href])=><a key={name} className="secondary" href={href} target="_blank" rel="noopener noreferrer">{name}</a>)}<button className="secondary" onClick={copy}>Copy link</button>{native&&<button className="secondary" onClick={()=>share()}>Share</button>}<a className="secondary" href={`/api/og?${new URLSearchParams({speaker_id:m.person_id,topic})}`} target="_blank" rel="noopener noreferrer">Download quote card</a><button className="secondary" onClick={()=>setOpen(!open)} aria-expanded={open}>Share with friends &amp; family</button></div>{open&&<section className="share-sheet"><h3>Share with friends &amp; family</h3><p>Choose who to send this to from your own phone or email. Contacts are read only if you choose Pick contacts; they are never uploaded to On the Record.</p><div className="actions">{native?<button className="primary" onClick={()=>share(true)}>Choose from my apps</button>:<><button className="secondary" onClick={copy}>Copy link</button><a className="secondary" href={emailLink('',title,friends)}>Email a friend</a></>}{picker&&<button className="secondary" onClick={contacts}>Pick contacts</button>}<button className="secondary" onClick={()=>setOpen(false)}>Close</button></div></section>}{notice&&<p role="status">{notice}</p>}</div>;
}
