import test from 'node:test';
import assert from 'node:assert/strict';
import {emailTemplate,emailLink,newest,formatDate} from './emailTemplate';
import {petitionTemplate} from './petitionTemplate';
import {ATTRIBUTION,type Member,type Quote,type Timeline} from './types';

const member:Member={person_id:'10758',name:'Example Person',house:'Senate',party:'Example party',electorate:'',state:'Victoria',image_url:''};
function quote(date:string,text:string):Quote{return {speech_id:date,speaker_id:member.person_id,speaker_name:member.name,date,house:'Senate',party:member.party,debate_title:'Debate',quote:text,url:`https://www.openaustralia.org.au/senate/?id=${date}`,verified:true};}
const quotes=[quote('2025-01-02','A “verbatim” quote—with punctuation & spaces.'),quote('2026-08-10','The newest text: café, Māori, 中文.'),quote('2025-02-01','Third quote.'),quote('2026-01-01','Second newest quote.')];
function result(items=quotes,complete=false):Timeline{return {status:items.length?'verified':complete?'no_matches':'incomplete_coverage',items,message:'',attribution:ATTRIBUTION,tool_calls:[],latency_ms:0,coverage:{complete,from:'2025-01-01',to:'2026-10-16',documents:542}};}

test('templates select at most three newest quotes without mutating input',()=>{
 const original=quotes.map(q=>q.speech_id);
 assert.deepEqual(newest(quotes).map(q=>q.date),['2026-08-10','2026-01-01','2025-02-01']);
 assert.deepEqual(quotes.map(q=>q.speech_id),original);
 for(const text of [emailTemplate(member,'housing',result()).body,petitionTemplate(member,'housing',result()).body]){
  assert.equal(text.split('\n').filter(line=>line.startsWith('- ')).length,3);
  const positions=newest(quotes).map(q=>text.indexOf(q.quote));
  assert.ok(positions[0]<positions[1]&&positions[1]<positions[2]);
  assert.ok(!text.includes(quotes[0].quote));
 }
});

test('quotes, source links, attribution and literal placeholders survive byte-for-byte',()=>{
 const q=quote('2026-08-10','Exact  double spaces\nand “quotes”, Unicode: Māori & café.');
 const email=emailTemplate(member,'housing & rent',result([q]));
 const petition=petitionTemplate(member,'housing & rent',result([q]));
 for(const body of [email.body,petition.body]){
  assert.ok(Buffer.from(body).includes(Buffer.from(q.quote)));
  assert.ok(body.includes(q.url));assert.ok(body.endsWith(ATTRIBUTION));
 }
 assert.ok(email.body.includes('Dear Example Person,'));
 assert.ok(email.body.includes('I am a constituent in Victoria.'));
 for(const placeholder of ['[Write your question or comment here.]','[Your name]','[Your suburb and postcode]'])assert.ok(email.body.includes(placeholder));
 assert.ok(petition.body.includes('[Explain here what you are asking for and why.]'));
 assert.ok(petition.body.includes('To: Example Person, Senator for Victoria'));
 assert.equal(email.text,`Subject: ${email.subject}\n\n${email.body}`);
});

test('partial empty coverage does not claim global absence',()=>{
 for(const body of [emailTemplate(member,'housing',result([],false)).body,petitionTemplate(member,'housing',result([],false)).body]){
  assert.ok(body.includes('currently indexed material'));
  assert.ok(body.includes('Coverage is incomplete'));
  assert.ok(!body.includes('since 1 January 2025'));
  assert.ok(body.endsWith(ATTRIBUTION));
 }
});

test('complete empty coverage uses the requested absence line and empty petition title',()=>{
 assert.ok(emailTemplate(member,'housing',result([],true)).body.includes('The Hansard record shows no statements by you on housing since 1 January 2025.'));
 const petition=petitionTemplate(member,'housing',result([],true));
 assert.equal(petition.title,'Ask Example Person to speak on housing in Parliament');
 assert.ok(petition.body.includes('The Hansard record shows no statements by Example Person on housing since 1 January 2025.'));
 assert.ok(petition.body.includes('[Explain here what you are asking for and why.]'));
});

test('populated petition title and House role match requested wording',()=>{
 const house={...member,house:'House',electorate:'Melbourne'};
 const petition=petitionTemplate(house,'housing',result());
 assert.equal(petition.title,'Ask Example Person to address housing in Parliament');
 assert.ok(petition.body.includes('Member for Melbourne'));
 assert.equal(formatDate('2026-08-10'),'10 Aug 2026');
});

test('mailto encodes subject and body without losing quotes, newlines or attribution',()=>{
 const draft=emailTemplate(member,'rent & housing? #1',result());
 const href=emailLink('example@aph.gov.au',draft.subject,draft.body);
 assert.ok(href.startsWith('mailto:example@aph.gov.au?subject='));
 assert.ok(href.includes('%26'));assert.ok(href.includes('%0A'));
 const url=new URL(href);
 assert.equal(url.searchParams.get('subject'),draft.subject);
 assert.equal(url.searchParams.get('body'),draft.body);
 assert.equal([...url.searchParams.keys()].length,2);
});
