import ProgressPanel from './components/ProgressPanel.js';
import ProfileBadge from './components/ProfileBadge.js';
import { createApp, ref, computed, onUnmounted, nextTick } from '/vendor/vue.esm-browser.prod.js';
import AppSidebar from './components/AppSidebar.js';
import { useTheme } from './composables/useTheme.js';
import { useDailyHabits } from './composables/useDailyHabits.js';

createApp({
  components: { ProgressPanel, ProfileBadge, AppSidebar },
  setup() {
    const theming = useTheme(), daily = useDailyHabits();
    const routines = ref([]), checks = ref([]), habits = ref([]), loading = ref(true), error = ref('');
    const selected = ref(null), remaining = ref(0), running = ref(false), finished = ref(false);
    const context = ref('desk'), checked = ref([]), interval = ref(30), reminders = ref(false), due = ref(false), nextReminder = ref(0), clock = ref(Date.now());
    let deadline = 0, breakOwner = null;
    const activeCheck = computed(() => checks.value.find(item => item.id === context.value));
    const time = computed(() => `${Math.floor(remaining.value / 60)}:${String(remaining.value % 60).padStart(2,'0')}`);
    const countdown = computed(() => Math.max(0, Math.ceil((nextReminder.value - clock.value)/60000)));
    const habitCount = computed(() => habits.value.filter(item => daily.completedHabits.value.includes(item.id)).length);
    async function load() {
      loading.value = true; error.value = '';
      try {
        const results = await Promise.all(['breaks','posture-checks','daily-habits'].map(async path => {
          const response = await fetch('/api/v1/' + path); if (!response.ok) throw Error(); return response.json();
        }));
        [routines.value, checks.value, habits.value] = results;
      } catch { error.value = 'We couldn’t load your coaching tools. Please try again.'; }
      finally { loading.value = false; await nextTick(); if (window.location.hash === '#posture-title') document.getElementById('posture-title')?.scrollIntoView(); }
    }
    function pause() {
      if (running.value) remaining.value = Math.max(0, Math.ceil((deadline - Date.now())/1000));
      running.value = false;
    }
    function choose(item) { pause(); selected.value = item; remaining.value = item.duration; finished.value = false; due.value = false; if (reminders.value) restartReminder(); }
    function start() { if (!selected.value || running.value || finished.value) return; if (remaining.value === selected.value.duration) breakOwner = daily.activityIdentity.value; deadline = Date.now() + remaining.value * 1000; running.value = true; }
    function reset() { pause(); remaining.value = selected.value.duration; finished.value = false; }
    function toggleReminders() { reminders.value = !reminders.value; due.value = false; nextReminder.value = Date.now() + Number(interval.value)*60000; }
    function restartReminder() { due.value = false; nextReminder.value = Date.now() + Number(interval.value)*60000; }
    function snooze() { due.value = false; nextReminder.value = Date.now() + 5*60000; }
    function changeContext(id) { context.value = id; checked.value = []; }
    function toggleCheck(index) { checked.value = checked.value.includes(index) ? checked.value.filter(x => x !== index) : [...checked.value,index]; }
    const ticker = setInterval(() => {
      clock.value = Date.now();
      if (running.value) {
        remaining.value = Math.max(0, Math.ceil((deadline - clock.value)/1000));
        if (remaining.value === 0) { running.value = false; finished.value = true; daily.recordBreak(breakOwner); if (reminders.value) restartReminder(); }
      }
      if (reminders.value && !running.value && clock.value >= nextReminder.value) due.value = true;
    }, 250);
    onUnmounted(() => clearInterval(ticker));
    load();
    return { ...theming, ...daily, routines, checks, habits, loading, error, load, selected, remaining, running, finished, context, checked, activeCheck, time, choose, start, pause, reset, interval, reminders, due, countdown, toggleReminders, restartReminder, snooze, changeContext, toggleCheck, habitCount };
  },
  template: `<div class="shell"><app-sidebar active="breaks"/><div class="content">
    <header><div class="breadcrumb">Your wellbeing <span>/</span><b>Breaks & daily habits</b></div><div class="topbar-tools"><label class="theme-picker"><span>Appearance</span><select :value="theme" @change="selectTheme($event.target.value)" aria-label="Color theme"><option v-for="item in themes" :key="item.id" :value="item.id">{{ item.label }}</option></select></label><profile-badge/></div></header>
    <main class="coach-page">
    <div class="page-heading"><div class="eyebrow">A LITTLE MOVEMENT, EVERY DAY</div><h1>Build a better break.</h1><p>Choose a reset, check your setup, and make movement part of your day.</p></div>
    <p v-if="loading" role="status" class="empty">Loading your coaching tools…</p><div v-else-if="error" role="alert" class="empty">{{ error }} <button @click="load">Try again</button></div>
    <template v-else>
      <p class="social-muted" role="status">{{ activityNotice }}</p><button v-if="!activityReady && activityMode === 'unavailable'" class="secondary" @click="retryActivity">Retry activity storage</button>
      <section class="reminder-panel" aria-labelledby="reminder-title"><div><h2 id="reminder-title">Your break rhythm</h2><p>{{ reminders ? 'Next reminder in about ' + countdown + ' minutes.' : 'Make a little space to move between tasks.' }}</p><small>Reminders work while this page is open. Background tabs may delay alerts.</small></div><div class="reminder-controls"><label>Every <select v-model="interval" @change="restartReminder"><option :value="20">20 minutes</option><option :value="30">30 minutes</option><option :value="45">45 minutes</option><option :value="60">60 minutes</option></select></label><button class="primary" @click="toggleReminders">{{ reminders ? 'Stop reminders' : 'Start reminders' }}</button></div></section>
      <div v-if="due" class="break-due" role="status"><b>Time for a little movement.</b><p>Choose a break below when it suits you.</p><button class="secondary" @click="snooze">Snooze 5 minutes</button><button class="secondary" @click="restartReminder">Skip this reminder</button></div>
      <section aria-labelledby="break-title"><div class="coach-section-heading"><h2 id="break-title">Enhanced breaks</h2><span>{{ completedBreaks }} completed today</span></div><div class="break-options"><button v-for="item in routines" :key="item.id" class="break-option" :class="{chosen: selected?.id === item.id}" :aria-pressed="selected?.id === item.id" @click="choose(item)"><span>{{ item.duration }} sec</span><h3>{{ item.name }}</h3><p>{{ item.description }}</p><b>Choose break ↗</b></button></div>
        <article v-if="selected" class="routine-panel" aria-labelledby="routine-title"><div class="routine-guide"><div class="eyebrow">YOUR CHOSEN RESET</div><h2 id="routine-title">{{ selected.name }}</h2><ol><li v-for="step in selected.steps">{{ step }}</li></ol><p class="care-note">{{ selected.caution }}</p></div><div class="routine-clock"><div class="timer" role="timer" aria-label="Time remaining">{{ time }}</div><p v-if="finished" class="success" role="status">Break complete. Check the activity status below for saving errors.</p><div class="routine-actions"><button v-if="!finished" class="primary" :disabled="!running && (!activityReady || savingActivity)" @click="running ? pause() : start()">{{ running ? 'Pause' : remaining === selected.duration ? 'Start break' : 'Resume' }}</button><button class="secondary" @click="reset">{{ finished ? 'Do it again' : 'Reset' }}</button></div></div></article>
      </section>
      <div class="coach-columns"><section class="coach-panel" aria-labelledby="posture-title"><div class="eyebrow">NOTICE, ADJUST, MOVE</div><h2 id="posture-title">Contextual posture checks</h2><div class="tabs"><button v-for="item in checks" :key="item.id" :class="{selected: context === item.id}" :aria-pressed="context === item.id" @click="changeContext(item.id)">{{ item.name }}</button></div><div v-if="activeCheck" class="checklist"><label v-for="(item,index) in activeCheck.items" :key="context + index"><input type="checkbox" :checked="checked.includes(index)" @change="toggleCheck(index)"><span>{{ item }}</span></label></div><p v-if="activeCheck && checked.length === activeCheck.items.length" class="success" role="status">Setup checked. Keep changing position comfortably.</p><small>A self-check, not camera-based monitoring. Recheck whenever your setup changes.</small></section>
      <section class="coach-panel" aria-labelledby="habits-title"><div class="eyebrow">{{ day }}</div><h2 id="habits-title">Daily movement habits</h2><p>{{ habitCount }} of {{ habits.length }} habits completed today</p><progress :value="habitCount" :max="Math.max(habits.length,1)" aria-label="Today's habit progress"></progress><div class="checklist"><label v-for="item in habits" :key="item.id"><input type="checkbox" :disabled="!activityReady || savingActivity" :checked="completedHabits.includes(item.id)" @change="toggleHabit(item.id)"><span><b>{{ item.name }}</b><small>{{ item.cue }}</small></span></label></div><small>{{ activityNotice }}</small><p v-if="storageWarning" role="status">{{ storageWarning }}</p></section></div>
      <progress-panel :day="day" :mode="activityMode" :identity="activityIdentity" :habits="completedHabits" :breaks="completedBreaks" :ready="activityReady" :saving="savingActivity"/>
      <footer><span>Guidance: <a href="https://www.nhs.uk/live-well/exercise/sitting-exercises/" target="_blank" rel="noopener">NHS sitting exercises</a> · <a href="https://www.osha.gov/etools/computer-workstations/positions" target="_blank" rel="noopener">OSHA workstation positions</a></span><span>PosturePal v0.10.0</span></footer>
    </template>
  </main></div></div>`
}).mount('#app');
