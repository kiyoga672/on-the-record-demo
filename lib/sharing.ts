import {ATTRIBUTION} from './types';
export const findingPath=(id:string,topic:string)=>`/speaker/${encodeURIComponent(id)}?${new URLSearchParams({topic})}`;
export function shareLinks(name:string,topic:string,url:string){
 const text=`What ${name} has said in Parliament on ${topic} — verified Hansard quotes. ${ATTRIBUTION}`;
 const enc=encodeURIComponent;
 return {text,links:{X:`https://twitter.com/intent/tweet?text=${enc(text)}&url=${enc(url)}`,Facebook:`https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`,WhatsApp:`https://wa.me/?text=${enc(text+' '+url)}`,LinkedIn:`https://www.linkedin.com/sharing/share-offsite/?url=${enc(url)}`}};
}
