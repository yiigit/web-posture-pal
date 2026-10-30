import AppSidebar from './components/AppSidebar.js';
import ProfileBadge from './components/ProfileBadge.js';
import { createApp, ref } from '/vendor/vue.esm-browser.prod.js';

createApp({
 components: { AppSidebar, ProfileBadge },
  setup() {
    const token = ref(''), authenticated = ref(false), exercises = ref([]), error = ref('');
    const busy = ref(false), editing = ref(null), form = ref(null), notice = ref('');
    const areas = ['Neck', 'Shoulders', 'Back', 'Wrists', 'Legs', 'Full body'];
    const positions = ['Seated', 'Standing', 'Seated or standing'];
    const symbols = ['neck', 'shoulders', 'twist', 'chest', 'wrists', 'reach', 'legs', 'walk'];
    const deleting = ref(null), view = ref('dashboard'), dashboard = ref(null);
    function navigate(destination) { view.value = destination; form.value = null; deleting.value = null; }
    async function request(path, method = 'GET', data) {
      const response = await fetch('/api/v1' + path, {
        method, cache: 'no-store', credentials: 'same-origin',
        headers: { 'X-PosturePal-Request':'1', ...(token.value ? {Authorization: `Bearer ${token.value}`} : {}), ...(data ? {'Content-Type': 'application/json'} : {}) },
        ...(data ? {body: JSON.stringify(data)} : {}),
      });
      if (!response.ok) {
        if (response.status === 401) { authenticated.value = false; token.value = ''; form.value = null; }
        const result = await response.json().catch(() => ({}));
        throw Error(Array.isArray(result.detail) ? result.detail.map(e => `${e.loc.slice(1).join('.')}: ${e.msg}`).join('; ') : result.detail || 'Request failed. Please try again.');
      }
      return response.status === 204 ? null : response.json();
    }
    async function load() {
      const [items, stats] = await Promise.all([request('/exercises'), request('/admin/dashboard')]);
      exercises.value = items; dashboard.value = stats;
    }
    async function refresh() {
      busy.value = true; error.value = '';
      try { await load(); } catch(e) { error.value = e.message; }
      finally { busy.value = false; }
    }
    async function login() {
      busy.value = true; error.value = '';
      try { await request('/admin/session'); authenticated.value = true; await load(); }
      catch (e) { error.value = e.message; }
      finally { busy.value = false; }
    }
    async function logout() {
      busy.value = true; error.value = '';
      try {
        await request('/auth/logout', 'POST');
        window.dispatchEvent(new Event('posturepal:account-changed'));
        try { localStorage.setItem('posturepal.auth.changed',String(Date.now())); } catch {}
        token.value = ''; authenticated.value = false; form.value = null; deleting.value = null;
        notice.value = ''; exercises.value = []; dashboard.value = null; view.value = 'dashboard';
      } catch(e) { error.value = e.message; }
      finally { busy.value = false; }
    }
    function edit(item = null) {
      view.value = 'movements';
      error.value = ''; notice.value = ''; editing.value = item?.id || null;
      form.value = item ? {...item, steps: item.steps.join('\n')} : {id:'', name:'', area:'Neck', duration:60, description:'', steps:'', position:'Seated', symbol:'neck'};
    }
    async function save() {
      busy.value = true; error.value = ''; notice.value = '';
      const data = {...form.value, steps: form.value.steps.split('\n').map(x => x.trim()).filter(Boolean)};
      if (editing.value) delete data.id;
      try {
        await request(editing.value ? `/exercises/${encodeURIComponent(editing.value)}` : '/exercises', editing.value ? 'PUT' : 'POST', data);
        form.value = null; notice.value = 'Movement saved.'; await load();
      } catch(e) { error.value = e.message; }
      finally { busy.value = false; }
    }
    async function remove() {
      busy.value = true; error.value = ''; notice.value = '';
      try {
        await request(`/exercises/${encodeURIComponent(deleting.value.id)}`, 'DELETE');
        deleting.value = null; notice.value = 'Movement deleted.'; await load();
      } catch(e) { error.value = e.message; }
      finally { busy.value = false; }
    }
    // Credentials intentionally live only in memory and disappear on reload/logout.
    return { dashboard, view, navigate, refresh, token, authenticated, exercises, error, busy, editing, form, notice, areas, positions, symbols, deleting, login, logout, edit, save, remove };
  },
  template: `<div class="shell"><app-sidebar active="admin"/><div class="content"><main class="admin-page"><div class="account-topbar"><a href="/" class="text-button">PosturePal dashboard</a><profile-badge/></div>
    <div class="admin-actions"><a href="/" class="text-button">← Back to dashboard</a><a href="/users.html" class="text-button">Manage users →</a><a href="/account.html" class="text-button">Your profile</a></div>
    <div class="admin-heading"><div><div class="eyebrow">POSTUREPAL ADMINISTRATION</div><h1>{{ view === 'dashboard' ? 'Your library at a glance.' : 'Manage movements.' }}</h1><p>Keep your movement library balanced, useful, and ready for a break.</p></div><button v-if="authenticated" class="secondary" @click="logout" :disabled="busy">Sign out</button></div>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p><p v-if="notice" role="status" class="success">{{ notice }}</p>
    <form v-if="!authenticated" @submit.prevent="login" class="admin-panel login-form">
      <h2>Administrator access</h2><p>Use your signed-in administrator account or enter the server administrator token.</p>
      <label>Administrator token<input v-model="token" type="password" minlength="32" autocomplete="off" spellcheck="false"></label>
      <button class="primary" :disabled="busy">{{ busy ? 'Checking…' : 'Sign in' }}</button>
    </form>
    <template v-else>
      <div class="admin-navigation"><nav aria-label="Administration"><button :class="{active: view === 'dashboard'}" :aria-current="view === 'dashboard' ? 'page' : undefined" @click="navigate('dashboard')" :disabled="busy">Dashboard</button><button :class="{active: view === 'movements'}" :aria-current="view === 'movements' ? 'page' : undefined" @click="navigate('movements')" :disabled="busy">Movements</button></nav><button class="secondary" @click="refresh" :disabled="busy">{{ busy ? 'Refreshing…' : 'Refresh data' }}</button></div>
      <section v-if="view === 'dashboard'" aria-label="Library dashboard">
        <template v-if="dashboard">
          <div class="dashboard-stats"><article><span>Movements</span><strong>{{ dashboard.total_exercises }}</strong><small>In your library</small></article><article><span>Quick breaks</span><strong>{{ dashboard.quick_breaks }}</strong><small>60 seconds or less</small></article><article><span>Average duration</span><strong>{{ dashboard.average_duration_seconds }}<em>sec</em></strong><small>Per movement</small></article><article><span>Total movement time</span><strong>{{ Math.round(dashboard.total_duration_seconds / 60 * 10) / 10 }}<em>min</em></strong><small>Across the catalog</small></article></div>
          <div class="dashboard-columns"><section class="admin-panel"><h2>Body-area coverage</h2><p>Find the gaps in your movement library.</p><div v-for="item in dashboard.body_areas" :key="item.area" class="coverage-row"><div><span>{{ item.area }}</span><b>{{ item.count }} movements</b></div><meter min="0" :max="Math.max(dashboard.total_exercises, 1)" :value="item.count" :aria-label="item.area + ' coverage'"></meter></div></section><section class="admin-panel"><h2>Movement positions</h2><p>Options for different spaces and moments.</p><ul class="position-summary"><li v-for="item in dashboard.positions" :key="item.position"><span>{{ item.position }}</span><b>{{ item.count }}</b></li></ul><div class="dashboard-callout"><h3>Make room for movement.</h3><p>Add a fresh exercise or improve an existing one.</p><button class="primary" @click="edit()">+ Add movement</button><button class="text-button" @click="navigate('movements')">Manage all movements →</button></div></section></div>
          <div v-if="!dashboard.total_exercises" class="admin-panel"><h2>A fresh start</h2><p>Your catalog is empty. Add a movement to get started.</p><button class="primary" @click="edit()">Create your first movement</button></div>
          <p class="dashboard-footnote">Live catalog statistics. These describe your exercise library, not completed workouts or user activity.</p>
        </template><p v-else role="status">Dashboard data is unavailable. Use Refresh data to try again.</p>
      </section>
      <template v-else>
      <form v-if="form" @submit.prevent="save" class="admin-panel">
        <h2>{{ editing ? 'Edit movement' : 'New movement' }}</h2>
        <fieldset :disabled="busy" class="admin-fields"><label>Unique ID<input v-model="form.id" :disabled="!!editing" required maxlength="80" pattern="[a-z0-9]+(-[a-z0-9]+)*" placeholder="gentle-neck-stretch"></label>
        <label>Name<input v-model="form.name" required maxlength="100"></label>
        <label>Body area<select v-model="form.area"><option v-for="area in areas">{{ area }}</option></select></label>
        <label>Duration in seconds<input v-model.number="form.duration" type="number" min="5" max="3600" step="1" required></label>
        <label>Position<select v-model="form.position"><option v-for="position in positions">{{ position }}</option></select></label>
        <label>Illustration<select v-model="form.symbol"><option v-for="symbol in symbols">{{ symbol }}</option></select></label>
        <label class="wide">Description<textarea v-model="form.description" required maxlength="500" rows="2"></textarea></label>
        <label class="wide">Instructions — one step per line<textarea v-model="form.steps" required maxlength="20019" rows="5"></textarea></label></fieldset>
        <div class="admin-actions"><button class="primary" :disabled="busy">{{ busy ? 'Saving…' : 'Save movement' }}</button><button class="secondary" type="button" :disabled="busy" @click="form = null">Cancel</button></div>
      </form>
      <div v-else-if="deleting" class="admin-panel" role="region" aria-labelledby="delete-title"><h2 id="delete-title">Delete {{ deleting.name }}?</h2><p>This removes the movement from the library permanently.</p><div class="admin-actions"><button class="primary" @click="remove" :disabled="busy">{{ busy ? 'Deleting…' : 'Delete movement' }}</button><button class="secondary" @click="deleting = null" :disabled="busy">Cancel</button></div></div>
      <template v-else><div class="admin-list-heading"><h2>{{ exercises.length }} movements</h2><button class="primary" @click="edit()">+ New movement</button></div>
      <div class="admin-panel" v-if="!exercises.length">Your library is empty. Add your first movement.</div>
      <ul class="admin-list"><li v-for="item in exercises" :key="item.id"><div><b>{{ item.name }}</b><small>{{ item.area }} · {{ item.duration }} seconds · {{ item.id }}</small></div><div class="admin-actions"><button class="secondary" @click="edit(item)" :aria-label="'Edit ' + item.name">Edit</button><button class="secondary" @click="deleting = item" :aria-label="'Delete ' + item.name">Delete</button></div></li></ul></template>
      </template>
    </template>
  </main></div></div>`
}).mount('#app');
