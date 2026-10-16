import {test} from 'node:test';
import assert from 'node:assert/strict';
import {findingPath,shareLinks} from './sharing';
import {ATTRIBUTION} from './types';
test('canonical finding URL round trips punctuation and Unicode',()=>{
 const topic='housing & rent / 住房?';const path=findingPath('10758',topic);
 assert.equal(new URL(path,'https://example.test').searchParams.get('topic'),topic);
});
test('all social links preserve canonical URL without tracking and include attribution in text',()=>{
 const url='https://example.test'+findingPath('10758','housing & rent');
 const {links,text}=shareLinks('Example Name','housing & rent',url);
 assert.ok(text.includes(ATTRIBUTION));
 assert.equal(new URL(links.X).searchParams.get('url'),url);
 assert.equal(new URL(links.X).searchParams.get('text'),text);
 assert.equal(new URL(links.Facebook).searchParams.get('u'),url);
 assert.equal(new URL(links.WhatsApp).searchParams.get('text'),text+' '+url);
 assert.equal(new URL(links.LinkedIn).searchParams.get('url'),url);
 assert.ok(Object.values(links).every(x=>!x.includes('utm_')));
});
