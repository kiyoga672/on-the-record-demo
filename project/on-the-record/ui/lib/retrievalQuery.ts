import {topicVocabulary} from './verification';
// Debate headings are source evidence too: speakers need not repeat a heading
// verbatim in the body. Keep the conservative body gate for arbitrary topics.
export function topicEvidenceQuery(topic:string){
 return {bool:{should:[{match:{text:topicVocabulary(topic)}},{match_phrase:{debate_title:topic}}],minimum_should_match:1}};
}
