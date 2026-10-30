import {ref,computed,watch,onMounted,onUnmounted} from '/vendor/vue.esm-browser.prod.js';

export default {
 props:{day:String,mode:String,identity:String,habits:Array,breaks:Number,ready:Boolean,saving:Boolean},
 setup(props){
  const progress=ref(null),error=ref(''),range=ref(7),updated=ref(''),celebration=ref('');
  let request=0,disposed=false,previous=new Set(),previousIdentity=null;
  const guestProgress=computed(()=>{
   const count=props.habits?.length||0,breaks=props.breaks||0;
   const points=(count||breaks?10:0)+5*count+10*Math.min(breaks,3);
   return {points,level:Math.floor(points/100)+1,level_progress:points%100,totals:{breaks,habit_checks:count,active_days:count||breaks?1:0},history:[],
    motivation:count||breaks?'A little progress counts. Choose a pace that feels good.':'Your first small step can happen whenever you’re ready.',
    awards:[{id:'first-break',name:'First reset',description:'Complete one timed break.',symbol:'✦',type:'badge',progress:Math.min(breaks,1),target:1,earned:breaks>0},
    {id:'first-habit',name:'A small step',description:'Check off one daily habit.',symbol:'🌱',type:'badge',progress:Math.min(count,1),target:1,earned:count>0},
    {id:'balanced-day',name:'Daily balance',description:'Check all four habits today.',symbol:'◈',type:'badge',progress:count,target:4,earned:count===4}]};
  });
  const summary=computed(()=>props.mode==='guest'?guestProgress.value:progress.value);
  function observeAwards(data){
   const identity=props.identity;
   const earned=new Set(data.awards.filter(item=>item.earned).map(item=>item.id));
   if(previousIdentity===identity){
    const newly=data.awards.filter(item=>item.earned&&!previous.has(item.id));
    celebration.value=newly.length?'Achievement unlocked: '+newly.map(item=>item.name).join(', '):'';
   }else celebration.value='';
   previous=earned;previousIdentity=identity;
  }
  async function refresh(){
   if(!props.ready||props.saving)return;
   if(props.mode==='guest'){observeAwards(guestProgress.value);return;}
   if(props.mode!=='account')return;
   const current=++request,identity=props.identity;
   try{
    const response=await fetch('/api/v1/me/daily-activity/progress?day='+encodeURIComponent(props.day)+'&days='+range.value,{credentials:'same-origin',cache:'no-store',headers:{'X-PosturePal-User':identity}});
    if(!response.ok)throw Error();
    const data=await response.json();
    if(!disposed&&current===request&&identity===props.identity){progress.value=data;error.value='';updated.value=new Date().toLocaleTimeString();observeAwards(data);}
   }catch{if(!disposed&&current===request){error.value='Progress could not be refreshed. Your last saved activity is unchanged.';}}
  }
  watch(()=>[props.identity,props.mode],()=>{request++;progress.value=null;error.value='';celebration.value='';previous=new Set();previousIdentity=null;});
  watch(()=>[props.ready,props.saving,props.day,props.breaks,(props.habits||[]).join(','),range.value],refresh,{immediate:true});
  const tick=setInterval(()=>{if(document.visibilityState==='visible')refresh();},15000);
  function focus(){refresh();}
  onMounted(()=>window.addEventListener('focus',focus));
  onUnmounted(()=>{disposed=true;request++;clearInterval(tick);window.removeEventListener('focus',focus);});
  return{summary,error,range,updated,celebration,refresh};
 },
 template:`<section class="progress-panel home-panel" aria-labelledby="progress-title"><div class="progress-heading"><div><div class="eyebrow">YOUR OWN PACE</div><h2 id="progress-title">Achievements & momentum</h2></div><span class="progress-live">● {{mode==='account'?'Refreshes every 15 sec':'Live in this browser'}}</span></div>
 <p v-if="!ready" role="status" class="progress-note">Checking private activity storage…</p><p v-if="error" role="alert" class="progress-note">{{error}} <button @click="refresh" class="secondary">Retry</button></p>
 <template v-if="ready&&summary"><p class="progress-motivation">{{summary.motivation}}</p><p v-if="celebration" class="award-unlocked" role="status">{{celebration}}</p><div class="progress-overview"><div><strong>Level {{summary.level}}</strong><span>{{summary.points}} {{mode==='guest'?'today’s':'retained'}} points</span><progress :value="summary.level_progress" max="100" aria-label="Progress toward next level"></progress><small>{{summary.level_progress}} / 100 toward the next level</small></div><div><strong>{{summary.totals.active_days}}</strong><span>{{mode==='guest'?'Active day':'Active days in 90 days'}}</span></div><div><strong>{{summary.totals.breaks}}</strong><span>Recorded breaks</span></div><div><strong>{{summary.totals.habit_checks}}</strong><span>Habit checkmarks</span></div></div>
 <div v-if="mode==='account'" class="progress-history"><div class="progress-heading"><h3>Daily progress</h3><label>Show <select v-model.number="range"><option :value="7">7 days</option><option :value="30">30 days</option></select></label></div><div class="history-grid" :class="{'history-month':range===30}" role="list" aria-label="Daily recorded activity"><div v-for="item in summary.history" :key="item.day" role="listitem" :class="{active:item.active}" :title="item.day+': '+item.breaks+' breaks, '+item.habits+' habits'" :aria-label="item.day+': '+item.breaks+' breaks, '+item.habits+' habits'"><b>{{item.breaks}}</b><span>{{item.day.slice(5)}}</span><small>{{item.habits}} habits</small></div></div><p class="progress-note">Numbers show recorded breaks. Highlighted days have a break or a checked habit. Last refreshed {{updated}}.</p></div>
 <div class="award-grid"><article v-for="award in summary.awards" :key="award.id" class="award-card" :class="{earned:award.earned}"><span class="award-symbol" aria-hidden="true">{{award.symbol}}</span><div><small>{{award.type==='trophy'?'Trophy':'Badge'}} · {{award.earned?'Unlocked':'In progress'}}</small><h3>{{award.name}}</h3><p>{{award.description}}</p><progress :value="award.progress" :max="award.target" :aria-label="award.name+' progress'"></progress><small>{{award.progress}} / {{award.target}}</small></div></article></div>
 <p class="progress-note">{{mode==='guest'?'Guest badges reflect today only and reset with browser daily progress. Sign in for private multi-day trophies.':'Awards and points are recalculated from retained activity and can change when you uncheck habits, delete history, or older days expire.'}} Points reward a small daily rhythm: 10 per active day, 5 per habit and 10 per break for up to three breaks each day. No rankings or automatic sharing.</p><p class="progress-note">Self-reported activity, not verified exercise or medical progress. Rest days are welcome. No camera or sensor tracking.</p></template>
 <p v-else-if="ready&&!error" role="status" class="progress-note">Loading your progress…</p></section>`
};
