import {ref,onMounted} from '/vendor/vue.esm-browser.prod.js';
export default {
 setup(){
  const stats=ref(null),loading=ref(true),guest=ref(false),error=ref('');
  async function load(){loading.value=true;error.value='';try{const r=await fetch('/api/v1/social/statistics',{credentials:'same-origin',cache:'no-store'});if(r.status===401){guest.value=true;stats.value=null;}else if(!r.ok)throw Error();else{guest.value=false;stats.value=await r.json();}}catch{error.value='Social statistics are unavailable.';}finally{loading.value=false;}}
  onMounted(load);
  return{stats,loading,guest,error,load};
 },
 template:`<section class="home-panel home-library" aria-labelledby="community-summary"><div class="home-section-heading"><h2 id="community-summary">Your community</h2><a href="/social.html" class="text-button">Friends & sharing →</a></div><p v-if="loading" class="home-muted" role="status">Loading social statistics…</p><p v-else-if="guest" class="home-muted"><a href="/account.html">Sign in</a> to connect with friends and see your social statistics.</p><div v-else-if="error" role="alert"><p class="home-muted">{{error}}</p><button class="secondary" @click="load">Try again</button></div><div v-else class="home-stats"><article><span>Friends</span><strong>{{stats.friends}}</strong><small>{{stats.pending_requests}} incoming requests</small></article><article><span>Activities posted</span><strong>{{stats.activities}}</strong><small>{{stats.shared_activities}} set to friends-only</small></article><article><span>Cheers received</span><strong>{{stats.likes_received}}</strong><small>On your activities</small></article><article><span>Comments received</span><strong>{{stats.comments_received}}</strong><small>From your community</small></article></div></section>`
};
