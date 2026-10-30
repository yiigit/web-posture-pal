import { ref, onUnmounted } from '/vendor/vue.esm-browser.prod.js';

function localDay() {
  const now=new Date();
  return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
}
const guestKey='posturepal.daily';

export function useDailyHabits() {
  const day=ref(localDay()),completedHabits=ref([]),completedBreaks=ref(0),storageWarning=ref('');
  const activityReady=ref(false),savingActivity=ref(false),activityMode=ref('loading'),activityIdentity=ref(null);
  const activityNotice=ref('Checking how to save your activity…');
  let userId=null,epoch=0,disposed=false,mutation=0;
  function clear(){completedHabits.value=[];completedBreaks.value=0;}
  function apply(data){completedHabits.value=Array.isArray(data.habits)?data.habits:[];completedBreaks.value=Number.isSafeInteger(data.breaks)&&data.breaks>=0?data.breaks:0;}
  async function accountRequest(path,method='GET',payload,identity=userId){
    const response=await fetch('/api/v1/me/daily-activity'+path,{
      method,credentials:'same-origin',cache:'no-store',headers:{'X-PosturePal-Request':'1','X-PosturePal-User':identity,...(payload?{'Content-Type':'application/json'}:{})},
      ...(payload?{body:JSON.stringify(payload)}:{}),
    });
    if(!response.ok)throw Error('Saving account activity could not be confirmed. Check your connection or sign in again.');
    return response.status===204?null:response.json();
  }
  function readGuest(fallback){
    try{const saved=JSON.parse(localStorage.getItem(guestKey)||'{}');if(saved.day===day.value)apply(saved);else if(saved.day)localStorage.removeItem(guestKey);}
    catch{if(fallback)apply(fallback);storageWarning.value='Browser storage is unavailable. Guest progress lasts for this visit only.';}
  }
  function persistGuest(){
    try{localStorage.setItem(guestKey,JSON.stringify({day:day.value,habits:completedHabits.value,breaks:completedBreaks.value}));}
    catch{storageWarning.value='Browser storage is unavailable. Guest progress lasts for this visit only.';}
  }
  async function load(){
    const fallback=activityMode.value==='guest'&&day.value===localDay()?{habits:[...completedHabits.value],breaks:completedBreaks.value}:null;
    const current=++epoch;activityReady.value=false;activityMode.value='loading';day.value=localDay();clear();userId=null;storageWarning.value='';
    try{
      const response=await fetch('/api/v1/users/me',{credentials:'same-origin',cache:'no-store'});
      if(disposed||current!==epoch)return;
      if(response.status===401){
        activityMode.value='guest';activityIdentity.value='guest';readGuest(fallback);activityNotice.value='Guest mode: daily activity stays in this browser and resets each local day.';
      }else if(response.ok){
        const user=await response.json();
        const data=await accountRequest('/'+day.value,'GET',undefined,user.id);
        if(disposed||current!==epoch)return;
        userId=user.id;activityIdentity.value=user.id;apply(data);activityMode.value='account';
        activityNotice.value='Private account activity: saved across devices for 90 days. Never shared automatically.';
      }else throw Error();
      if(current===epoch)activityReady.value=true;
    }catch{
      if(current===epoch&&!disposed){activityMode.value='unavailable';activityIdentity.value=null;clear();storageWarning.value='Activity storage could not be verified. Retry before recording; account data will not be written into guest storage.';activityNotice.value='Activity recording is paused.';}
    }
  }
  async function save(kind,id){
    if(!activityReady.value||savingActivity.value)return;
    if(day.value!==localDay()){await load();if(!activityReady.value)return;}
    const current=epoch,identity=userId;mutation++;
    if(activityMode.value==='guest'){
      if(kind==='habit')completedHabits.value=completedHabits.value.includes(id)?completedHabits.value.filter(x=>x!==id):[...completedHabits.value,id];
      else completedBreaks.value++;
      persistGuest();return;
    }
    if(activityMode.value!=='account')return;
    savingActivity.value=true;storageWarning.value='';
    try{
      const data=kind==='habit'
        ?await accountRequest('/'+day.value+'/habits/'+encodeURIComponent(id),'PUT',{completed:!completedHabits.value.includes(id)},identity)
        :await accountRequest('/'+day.value+'/breaks','POST',{event_id:crypto.randomUUID()},identity);
      if(current===epoch&&!disposed)apply(data);
      try{localStorage.setItem('posturepal.activity.changed',String(Date.now()));}catch{}
    }catch(error){if(current===epoch&&!disposed)storageWarning.value=error.message;}
    finally{savingActivity.value=false;}
  }
  async function clearDailyActivity(){
    if(!activityReady.value||savingActivity.value)return;
    const current=epoch;savingActivity.value=true;
    try{
      if(activityMode.value==='account')await accountRequest('','DELETE');
      else localStorage.removeItem(guestKey);
      if(current===epoch)clear();
      window.dispatchEvent(new Event('posturepal:activity-changed'));
      try{localStorage.setItem('posturepal.activity.changed',String(Date.now()));}catch{}
    }catch{storageWarning.value='Could not delete activity. Please try again.';}
    finally{savingActivity.value=false;}
  }
  async function exportDailyActivity(){
    if(!activityReady.value)return;
    try{
      const data=activityMode.value==='account'?await accountRequest(''):{daily_activity:[{day:day.value,habits:completedHabits.value,breaks:completedBreaks.value}]};
      const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
      const link=document.createElement('a');link.href=url;link.download='posturepal-daily-activity.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch{storageWarning.value='Could not export activity. Please try again.';}
  }
  async function refreshActivity(){
    if(!activityReady.value||savingActivity.value||activityMode.value!=='account')return;
    const current=epoch,identity=userId,observedMutation=mutation;
    try{
      const data=await accountRequest('/'+day.value,'GET',undefined,identity);
      if(!disposed&&current===epoch&&observedMutation===mutation&&!savingActivity.value)apply(data);
    }catch{if(!disposed&&current===epoch)load();}
  }
  const liveTimer=setInterval(()=>{if(typeof document==='undefined'||document.visibilityState==='visible')refreshActivity();},15000);
  function focus(){if(!savingActivity.value)load();}
  function sync(event){if([guestKey,'posturepal.auth.changed','posturepal.activity.changed'].includes(event.key))focus();}
  function changed(){load();}
  const timer=setInterval(()=>{if(day.value!==localDay()&&!savingActivity.value)load();},1000);
  window.addEventListener('storage',sync);window.addEventListener('focus',focus);
  window.addEventListener('posturepal:account-changed',changed);window.addEventListener('posturepal:activity-changed',focus);
  onUnmounted(()=>{disposed=true;epoch++;clearInterval(timer);clearInterval(liveTimer);window.removeEventListener('storage',sync);window.removeEventListener('focus',focus);window.removeEventListener('posturepal:account-changed',changed);window.removeEventListener('posturepal:activity-changed',focus);});
  load();
  return{day,completedHabits,completedBreaks,storageWarning,activityReady,savingActivity,activityMode,activityIdentity,activityNotice,retryActivity:load,toggleHabit:id=>save('habit',id),recordBreak:async(expectedIdentity=activityIdentity.value)=>{
    const deadline=Date.now()+30000;
    while((savingActivity.value||activityMode.value==='loading')&&!disposed&&Date.now()<deadline)await new Promise(resolve=>setTimeout(resolve,50));
    if(disposed)return;
    if(!activityReady.value||expectedIdentity!==activityIdentity.value){storageWarning.value='Break was not saved because the account changed or storage is unavailable. No activity was transferred to another account.';return;}
    return save('break');
  },clearDailyActivity,exportDailyActivity};
}
