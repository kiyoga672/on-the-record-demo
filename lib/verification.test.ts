import {test} from 'node:test';
import assert from 'node:assert/strict';
import {verifyCandidate,attentionScore,topicVocabulary,collectVerifiedQuotes} from './verification';
const s={speech_id:'representatives:2026-10-15.1',speaker_id:'1',speaker_name:'Test fixture',date:'2026-10-15',house:'House',party:'',debate_title:'Fixture',text:'The original sentence, with punctuation. Another sentence.',url:'https://www.openaustralia.org.au/debates/?id=2026-10-15.1'};
test('invalid first excerpt does not discard a valid second excerpt from the same speech',async()=>{
 const result=await collectVerifiedQuotes([{speech_id:s.speech_id,quote:'the original sentence,'},{speech_id:s.speech_id,quote:'The original sentence,'}],i=>Promise.resolve(verifyCandidate(s,'1',i.quote)));
 assert.equal(result.length,1);assert.equal(result[0].quote,'The original sentence,');
});
test('successful excerpts still deduplicate by speech and all invalid excerpts stay empty',async()=>{
 let calls=0;const validate=async(i:{quote:string})=>{calls++;return verifyCandidate(s,'1',i.quote);};
 const result=await collectVerifiedQuotes([{speech_id:s.speech_id,quote:'The original sentence,'},{speech_id:s.speech_id,quote:'Another sentence.'}],validate);
 assert.equal(result.length,1);assert.equal(calls,1);
 assert.deepEqual(await collectVerifiedQuotes([{speech_id:s.speech_id,quote:'Changed words.'},{speech_id:s.speech_id,quote:'the original sentence,'}],validate),[]);
});
test('exact contiguous quote passes',()=>assert.ok(verifyCandidate(s,'1','original sentence, with punctuation.')));
test('wrong speaker, mutation, token reorder, stitching and long quotes fail',()=>{
  assert.equal(verifyCandidate(s,'2','The original sentence,'),null);
  for(const q of ['the original sentence,','sentence original','The original ... Another sentence.']) assert.equal(verifyCandidate(s,'1',q),null);
  const long=Array(61).fill('word').join(' ');assert.equal(verifyCandidate({...s,text:long},'1',long),null);
});
test('untrusted and mismatched source chamber fails',()=>{
 assert.equal(verifyCandidate({...s,url:'https://evil.example/debates/?id=1'},'1','The original sentence,'),null);
 assert.equal(verifyCandidate({...s,house:'Senate'},'1','The original sentence,'),null);
 assert.equal(verifyCandidate({...s,date:'2024-12-31'},'1','The original sentence,'),null);
});
test('median and insufficient baseline',()=>{
 assert.equal(attentionScore(.2,[.1,.2,.3]),50);assert.equal(attentionScore(.15,[0,.1,.2,.3]),50);
 assert.equal(attentionScore(1,[0,0,0,1]),null);assert.equal(attentionScore(.1,[.1]),null);
});
test('known themes expand synonyms; unknown multiword themes require all tokens',()=>{
 assert.equal(topicVocabulary('HECS').operator,'or');assert.match(topicVocabulary('HECS').query,/indexation/);
 assert.deepEqual(topicVocabulary('quuxlorian teleportatorium'),{query:'quuxlorian teleportatorium',operator:'and'});
});
