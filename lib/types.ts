export const ATTRIBUTION = 'Source: Parliament of Australia Hansard via OpenAustralia.';
export type Member = {person_id:string;name:string;house:string;party:string;electorate:string;state:string;image_url:string};
export type Speech = {speech_id:string;speaker_id:string;speaker_name:string;date:string;house:string;party:string;debate_title:string;text:string;url:string};
export type Quote = Omit<Speech,'text'> & {quote:string;verified:true};
export type Timeline = {status:'verified'|'no_matches'|'incomplete_coverage'|'verification_failed';items:Quote[];message:string;attribution:string;tool_calls:string[];latency_ms:number;coverage:{complete:boolean;from:string;to:string;documents:number}};
