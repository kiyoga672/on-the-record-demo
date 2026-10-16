'use client';
import {useEffect,useRef,useState} from 'react';
import {ATTRIBUTION,type Member,type Timeline} from '@/lib/types';
import {emailTemplate,emailLink} from '@/lib/emailTemplate';
import {petitionTemplate} from '@/lib/petitionTemplate';
export default function TemplateActions({member,topic,result}:{member:Member;topic:string;result:Timeline}){
 const [mode,setMode]=useState<'email'|'petition'|null>(null),[notice,setNotice]=useState(''),[contact,setContact]=useState<{email:string|null;contact_url:string}|null>(null);
 const dialog=useRef<HTMLElement>(null),trigger=useRef<HTMLElement>(null);
 const draft=emailTemplate(member,topic,result),petition=petitionTemplate(member,topic,result);
 useEffect(()=>{if(mode!=='email')return;setContact(null);let alive=true;fetch(`/api/contact?speaker_id=${member.person_id}`).then(r=>r.ok?r.json():null).then(x=>{if(alive)setContact(x);}).catch(()=>{});return()=>{alive=false;};},[mode,member.person_id]);
 useEffect(()=>{if(!notice)return;const t=setTimeout(()=>setNotice(''),2000);return()=>clearTimeout(t);},[notice]);
 useEffect(()=>{
  if(!mode)return;
  const previous=trigger.current;
  const overflow=document.body.style.overflow;document.body.style.overflow='hidden';
  const key=(e:KeyboardEvent)=>{
   if(e.key==='Escape'){e.preventDefault();setMode(null);return;}
   if(e.key!=='Tab')return;
   const targets=Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), [tabindex="0"]')??[]);
   const first=targets[0],last=targets[targets.length-1];
   if(!first)return;
   if(e.shiftKey&&(document.activeElement===first||!dialog.current?.contains(document.activeElement))){e.preventDefault();last.focus();}
   else if(!e.shiftKey&&(document.activeElement===last||!dialog.current?.contains(document.activeElement))){e.preventDefault();first.focus();}
  };
  window.addEventListener('keydown',key);
  return()=>{window.removeEventListener('keydown',key);document.body.style.overflow=overflow;previous?.focus();};
 },[mode]);
 async function copy(text:string){try{await navigator.clipboard.writeText(text);setNotice('Copied');}catch{setNotice('Copy unavailable. Select and copy the text.');}}
 const contactUrl=contact?.contact_url??`https://www.aph.gov.au/Senators_and_Members/Parliamentarian_Search_Results?q=${encodeURIComponent(member.name)}`;
 return <><div className="actions"><button className="secondary" onClick={e=>{trigger.current=e.currentTarget;setNotice('');setMode('email');}}>Write to your MP</button><button className="secondary" onClick={e=>{trigger.current=e.currentTarget;setNotice('');setMode('petition');}}>Draft a petition</button></div>{mode&&<div className="modal-backdrop" onClick={()=>setMode(null)}><section ref={dialog} className="modal template-modal" role="dialog" aria-modal="true" aria-label={mode==='email'?'Write to your MP':'Draft a petition'} onClick={e=>e.stopPropagation()}><button className="secondary modal-close" autoFocus onClick={()=>setMode(null)}>Close</button><h2>{mode==='email'?'Write to your MP':'Draft a petition'}</h2>{mode==='email'?<><textarea aria-label="Email template" readOnly value={draft.text} rows={17}/><div className="actions"><button className="primary" onClick={()=>copy(draft.text)}>Copy email</button>{contact?.email&&draft.body.length<=1800?<a className="secondary" href={emailLink(contact.email,draft.subject,draft.body)}>Open in my email app</a>:<button className="secondary" disabled>Open in my email app</button>}<a href={contactUrl} target="_blank" rel="noopener noreferrer">Find their contact details ↗</a></div>{draft.body.length>1800&&<p>This draft is too long for a reliable mail link. Copy the full email to preserve the exact quotations.</p>}<p>Edit the constituent statement if it does not apply to you.</p><p>This opens your own email app. Nothing is sent by On the Record.</p></>:<><label htmlFor="petition-title">Title</label><input id="petition-title" readOnly value={petition.title}/><label htmlFor="petition-body">Body</label><textarea id="petition-body" readOnly value={petition.body} rows={14}/><div className="actions"><button className="secondary" onClick={()=>copy(petition.title)}>Copy title</button><button className="secondary" onClick={()=>copy(petition.body)}>Copy body</button><a className="primary" href="https://www.change.org/start-a-petition" target="_blank" rel="noopener noreferrer">Continue on change.org ↗</a></div><ol><li>Click Start a petition</li><li>Paste the title and body</li><li>Add your own ask</li></ol><p>Petitions are hosted by change.org, not by On the Record.</p></>}<p className="subtle">{ATTRIBUTION}</p>{notice&&<p role="status">{notice}</p>}</section></div>}</>;
}



