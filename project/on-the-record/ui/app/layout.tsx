import type {Metadata} from 'next';
import Link from 'next/link';
import './globals.css';
import {ATTRIBUTION} from '@/lib/types';
export const metadata:Metadata={title:'On the Record — Parliament, in their own words',description:'Find verified verbatim statements from Australian federal Hansard.'};
export default function Layout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><header className="site-header"><Link className="brand" href="/"><span className="brand-mark">or.</span> on the record<span className="brand-dot">●</span></Link><span className="header-note">AUSTRALIAN PARLIAMENT · PUBLIC RECORDS</span><span className="status-pill"><span/> SOURCE VERIFIED</span></header>{children}<footer><Link href="/saved">Saved quotes →</Link><br/><span>{ATTRIBUTION}</span><p>Quotes are verified against the Hansard index before display. We never paraphrase or score MPs by character.</p><span className="footer-motto">LLM for reasoning, Elastic for truth.</span></footer></body></html>;
}
