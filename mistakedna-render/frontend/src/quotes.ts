// Original MistakeDNA learning quotes; no attributed quotations or external requests.
export const QUOTES=[
'Every mistake is a clue. Decode yours.',
'A wrong answer can point to the right question.',
'Understanding grows when you ask why.',
'Small steps become strong foundations.',
'Check the reasoning, not just the result.',
'One careful correction can change the next attempt.',
'Confidence grows from evidence of understanding.',
'Practise the gap, then test the connection.',
'A difficult concept is an invitation to slow down.',
'Progress begins when a question becomes clearer.',
'Give your ideas a chance to be tested.',
'Learning is a sequence of useful discoveries.',
'The next breakthrough may begin with a small doubt.',
'Be curious about the answer you almost understood.',
'Precision is a habit built one step at a time.',
'A stronger explanation is a form of progress.',
'Connect one idea well before adding the next.',
'Returning to a concept is part of moving forward.',
'Let evidence guide your next learning step.',
'Your understanding can grow beyond today’s result.'
] as const;
function shuffled(cycle:number){
 const order=QUOTES.map((_,i)=>i);let seed=(cycle^0x6d2b79f5)>>>0;
 const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
 for(let i=order.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[order[i],order[j]]=[order[j],order[i]];}
 return order;
}
export function quoteForDate(date:Date):string{
 const day=Math.floor(Date.UTC(date.getFullYear(),date.getMonth(),date.getDate())/86400000);
 const cycle=Math.floor(day/QUOTES.length);const order=shuffled(cycle);
 if(order[0]===shuffled(cycle-1)[QUOTES.length-1])[order[0],order[1]]=[order[1],order[0]];
 const slot=((day%QUOTES.length)+QUOTES.length)%QUOTES.length;
 return QUOTES[order[slot]];
}
