import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const original=globalThis.posturepalSource ?? readFileSync(new URL('../frontend/src/composables/useDailyHabits.js',import.meta.url),'utf8');
const source=original.replace(/^import .*?;\n/,'const ref=value=>({value}); const onUnmounted=fn=>globalThis.cleanupHooks.push(fn);\n');
const {useDailyHabits}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function environment(user=null){
 globalThis.cleanupHooks=[];
 globalThis.window=new EventTarget();
 const saved=new Map();
 globalThis.localStorage={getItem:key=>saved.get(key)??null,setItem:(key,value)=>saved.set(key,value),removeItem:key=>saved.delete(key)};
 const state={user,fail:false,requests:[],records:new Map()};
 globalThis.fetch=async(path,options={})=>{
  state.requests.push({path,...options});
  if(state.fail)throw Error('Network unavailable');
  if(path==='/api/v1/users/me')return Response.json(state.user?{id:state.user}:{},{status:state.user?200:401});
  if(options.headers['X-PosturePal-User']!==state.user)return Response.json({},{status:409});
  const day=path.split('/')[5];
  const key=state.user+':'+day;
  let record=state.records.get(key)||{day,habits:[],breaks:0};
  if(options.method==='PUT'){
   const id=path.split('/').at(-1),payload=JSON.parse(options.body);
   record={...record,habits:payload.completed?[...new Set([...record.habits,id])]:record.habits.filter(x=>x!==id)};
   state.records.set(key,record);
  }
  if(options.method==='POST'){record={...record,breaks:record.breaks+1};state.records.set(key,record);}
  return Response.json(record);
 };
 return{state,saved,cleanup:()=>{for(const fn of cleanupHooks)fn();}};
}
async function ready(activity){for(let i=0;i<30&&!activity.activityReady.value&&activity.activityMode.value!=='unavailable';i++)await tick();}
function day(){const n=new Date();return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,'0')}-${String(n.getDate()).padStart(2,'0')}`;}

test('guest activity stays in the browser and never calls the daily API',async()=>{
 const env=environment();try{
  const activity=useDailyHabits();await ready(activity);
  await activity.toggleHabit('first-task');await activity.recordBreak();
  assert.equal(activity.activityMode.value,'guest');
  assert.equal(JSON.parse(env.saved.get('posturepal.daily')).breaks,1);
  assert.equal(env.state.requests.filter(r=>r.path.includes('daily-activity')).length,0);
 }finally{env.cleanup();}
});
test('account progress is isolated from guest history and is not cached locally',async()=>{
 const env=environment('user-a');try{
  env.saved.set('posturepal.daily',JSON.stringify({day:day(),habits:['desk-check'],breaks:9}));
  const activity=useDailyHabits();await ready(activity);
  assert.equal(activity.completedBreaks.value,0);
  await activity.toggleHabit('first-task');await activity.recordBreak();
  assert.equal(activity.completedBreaks.value,1);
  assert.equal(JSON.parse(env.saved.get('posturepal.daily')).breaks,9);
  env.state.user=null;window.dispatchEvent(new Event('posturepal:account-changed'));await ready(activity);
  assert.equal(activity.activityMode.value,'guest');assert.equal(activity.completedBreaks.value,9);
 }finally{env.cleanup();}
});
test('failed identity checks pause recording instead of falling back to guest storage',async()=>{
 const env=environment('user-a');try{
  env.state.fail=true;const activity=useDailyHabits();await ready(activity);
  await activity.recordBreak();await activity.toggleHabit('desk-check');
  assert.equal(activity.activityReady.value,false);assert.equal(activity.activityMode.value,'unavailable');
  assert.equal(env.saved.has('posturepal.daily'),false);
 }finally{env.cleanup();}
});
test('a stale account cannot write activity into a newly signed-in account',async()=>{
 const env=environment('user-a');try{
  const activity=useDailyHabits();await ready(activity);env.state.user='user-b';
  await activity.toggleHabit('desk-check');
  assert.equal(env.state.records.size,0);assert.equal(env.saved.has('posturepal.daily'),false);
  assert.match(activity.storageWarning.value,/could not be confirmed/);
 }finally{env.cleanup();}
});
test('a break started by another identity is not reassigned after login',async()=>{
 const env=environment('user-b');try{
  const activity=useDailyHabits();await ready(activity);
  await activity.recordBreak('user-a');
  assert.equal(env.state.records.size,0);
  assert.match(activity.storageWarning.value,/account changed/);
 }finally{env.cleanup();}
});

test('blocked browser storage preserves in-memory guest progress on focus',async()=>{
 const env=environment();try{
  globalThis.localStorage={getItem:()=>{throw Error();},setItem:()=>{throw Error();},removeItem:()=>{throw Error();}};
  const activity=useDailyHabits();await ready(activity);await activity.recordBreak();
  window.dispatchEvent(new Event('focus'));await ready(activity);
  assert.equal(activity.completedBreaks.value,1);
  assert.match(activity.storageWarning.value,/visit only/);
 }finally{env.cleanup();}
});

test('visible-page polling refreshes account progress and hidden tabs skip polling',async()=>{
 const env=environment('user-a'),originalInterval=globalThis.setInterval,pollers=[];
 globalThis.setInterval=(fn,delay)=>{if(delay===15000)pollers.push(fn);return originalInterval(fn,delay);};
 try{
  const activity=useDailyHabits();await ready(activity);
  env.state.records.set('user-a:'+day(),{day:day(),habits:['desk-check'],breaks:4});
  pollers[0]();await tick();await tick();
  assert.equal(activity.completedBreaks.value,4);
  assert.deepEqual(activity.completedHabits.value,['desk-check']);
  globalThis.document={visibilityState:'hidden'};
  const count=env.state.requests.length;pollers[0]();await tick();
  assert.equal(env.state.requests.length,count);
 }finally{env.cleanup();globalThis.setInterval=originalInterval;delete globalThis.document;}
});

test('an older poll response cannot overwrite a newly saved habit',async()=>{
 const env=environment('user-a'),originalInterval=globalThis.setInterval,pollers=[];
 globalThis.setInterval=(fn,delay)=>{if(delay===15000)pollers.push(fn);return originalInterval(fn,delay);};
 try{
  const activity=useDailyHabits();await ready(activity);
  const originalFetch=globalThis.fetch;let finishPoll;
  globalThis.fetch=async(path,options)=>{
   if(path.includes('daily-activity')&&options.method==='GET')return new Promise(resolve=>{finishPoll=()=>resolve(Response.json({day:day(),habits:[],breaks:0}));});
   return originalFetch(path,options);
  };
  pollers[0]();await tick();
  await activity.toggleHabit('first-task');
  finishPoll();await tick();await tick();
  assert.deepEqual(activity.completedHabits.value,['first-task']);
 }finally{env.cleanup();globalThis.setInterval=originalInterval;}
});
