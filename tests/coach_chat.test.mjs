import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../frontend/src/composables/useCoachChat.js',import.meta.url),'utf8')
  .replace(/^import .*?;\n/,'const ref=value=>({value});const onMounted=fn=>globalThis.mountHooks.push(fn);const onUnmounted=fn=>globalThis.cleanupHooks.push(fn);\n');
const {useCoachChat}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function settle(){for(let i=0;i<10;i++)await tick();}
function environment(user={id:'alice',display_name:'Alice'}){
  globalThis.mountHooks=[];globalThis.cleanupHooks=[];
  globalThis.window=new EventTarget();globalThis.document=new EventTarget();document.hidden=false;
  const originalInterval=globalThis.setInterval,originalClear=globalThis.clearInterval;
  let interval;
  globalThis.setInterval=fn=>{interval=fn;return 1;};globalThis.clearInterval=()=>{};
  globalThis.localStorage={getItem:()=>{throw Error('Chat must not read localStorage');},setItem:()=>{throw Error('Chat must not write localStorage');}};
  const state={user,enabled:true,requests:[],delay:null,fail:false};
  globalThis.fetch=async(path,options={})=>{
    state.requests.push({path,...options});
    if(state.fail)throw Error('offline');
    if(path==='/api/v1/users/me')return Response.json(state.user??{},{status:state.user?200:401});
    if(path.includes('/context'))return Response.json({enabled:state.enabled,context:{profile:state.user,progress:{points:10}}});
    if(path.endsWith('/messages')){
      if(state.delay)return state.delay;
      return Response.json({reply:'One small step counts.'});
    }
    throw Error('unexpected path');
  };
  const chat=useCoachChat();mountHooks.forEach(fn=>fn());
  return {state,chat,poll:()=>interval(),cleanup(){cleanupHooks.forEach(fn=>fn());globalThis.setInterval=originalInterval;globalThis.clearInterval=originalClear;}};
}
test('requires verified account, configured provider and consent before sending',async()=>{
  const env=environment();try{
    await settle();env.chat.draft.value='Help me';await env.chat.send();
    assert.equal(env.state.requests.filter(r=>r.path.endsWith('/messages')).length,0);
    env.chat.consent.value=true;await env.chat.send();
    const sent=env.state.requests.find(r=>r.path.endsWith('/messages'));
    assert.equal(sent.headers['X-PosturePal-User'],'alice');
    assert.equal(sent.headers['X-PosturePal-Request'],'1');
    assert.equal(JSON.parse(sent.body).consent,true);
    assert.equal(env.chat.messages.value.length,2);
    env.chat.clearChat();assert.equal(env.chat.consent.value,false);assert.equal(env.chat.messages.value.length,0);
  }finally{env.cleanup();}
});
test('account changes discard in-flight answers and consent',async()=>{
  const env=environment();try{
    await settle();let finish;
    env.state.delay=new Promise(resolve=>{finish=resolve;});
    env.chat.consent.value=true;env.chat.draft.value='Private Alice message';const pending=env.chat.send();
    env.state.user={id:'bob',display_name:'Bob'};
    window.dispatchEvent(new Event('posturepal:account-changed'));await settle();
    finish(Response.json({reply:'Private Alice answer'}));await pending;
    assert.equal(env.chat.user.value.id,'bob');assert.equal(env.chat.messages.value.length,0);
    assert.equal(env.chat.draft.value,'');assert.equal(env.chat.consent.value,false);
  }finally{env.cleanup();}
});
test('failed identity refresh clears personal state and does not become guest activity',async()=>{
  const env=environment();try{
    await settle();env.chat.consent.value=true;env.chat.draft.value='Help';await env.chat.send();
    env.state.fail=true;await env.chat.refresh();
    assert.equal(env.chat.user.value,null);assert.equal(env.chat.context.value,null);
    assert.equal(env.chat.messages.value.length,0);assert.equal(env.chat.consent.value,false);
  }finally{env.cleanup();}
});
test('guests and unconfigured users cannot send; hidden tabs pause identity polling',async()=>{
  const env=environment(null);try{
    await settle();env.chat.draft.value='Help';env.chat.consent.value=true;await env.chat.send();
    assert.equal(env.state.requests.filter(r=>r.path.endsWith('/messages')).length,0);
    document.hidden=true;const before=env.state.requests.length;env.poll();await settle();assert.equal(env.state.requests.length,before);
    env.state.user={id:'bob'};env.state.enabled=false;document.hidden=false;env.poll();await settle();
    env.chat.consent.value=true;env.chat.draft.value='Help';await env.chat.send();
    assert.equal(env.state.requests.filter(r=>r.path.endsWith('/messages')).length,0);
  }finally{env.cleanup();}
});
