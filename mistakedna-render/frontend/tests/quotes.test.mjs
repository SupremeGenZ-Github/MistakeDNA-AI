import test from 'node:test';
import assert from 'node:assert/strict';
import {QUOTES,quoteForDate} from '../src/quotes.ts';
test('twenty distinct quotes stay stable for the same local calendar day',()=>{
 assert.equal(QUOTES.length,20);assert.equal(new Set(QUOTES).size,20);
 assert.equal(quoteForDate(new Date(2026,9,29,0,0)),quoteForDate(new Date(2026,9,29,23,59)));
});
test('each aligned 20-day cycle is a permutation, with no repeat across midnight or cycle boundaries',()=>{
 const start=Math.ceil(Math.floor(Date.UTC(2026,0,1)/86400000)/20)*20;
 const results=[];
 for(let i=0;i<400;i++){
  const u=new Date((start+i)*86400000);const local=new Date(u.getUTCFullYear(),u.getUTCMonth(),u.getUTCDate(),12);
  const quote=quoteForDate(local);results.push(quote);assert.ok(QUOTES.includes(quote));
  if(i>0)assert.notEqual(results[i],results[i-1]);
 }
 for(let i=0;i<400;i+=20)assert.equal(new Set(results.slice(i,i+20)).size,20);
});
test('leap-day and year boundaries return valid repeatable quotes',()=>{
 for(const date of [new Date(2028,1,29),new Date(2026,11,31),new Date(2027,0,1)])assert.equal(quoteForDate(date),quoteForDate(new Date(date)));
});
