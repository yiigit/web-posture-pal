import ProgressPanel from './components/ProgressPanel.js';
import SocialSummary from './components/SocialSummary.js';
import ProfileBadge from './components/ProfileBadge.js';
import { createApp, ref, computed } from '/vendor/vue.esm-browser.prod.js';
import { useDashboardStatistics } from './composables/useDashboardStatistics.js';
import { useTheme } from './composables/useTheme.js';
import { useLibrary } from './composables/useLibrary.js';
import { useDailyHabits } from './composables/useDailyHabits.js';
import AppSidebar from './components/AppSidebar.js';
import MovementFigure from './components/MovementFigure.js';

createApp({
  components: { ProgressPanel, SocialSummary, ProfileBadge, MovementFigure, AppSidebar },
  setup() {
    const theme = useTheme(), library = useLibrary(), daily = useDailyHabits();
    const habits = ref([]), habitError = ref(''), habitsLoading = ref(true);
    const statistics = useDashboardStatistics(library.exercises, habits, daily.completedHabits, library.favorites);
    const completedCount = computed(() => habits.value.filter(habit => daily.completedHabits.value.includes(habit.id)).length);
    const savedCount = computed(() => library.exercises.value.filter(item => library.favorites.value.includes(item.id)).length);
    async function loadHabits() {
      habitsLoading.value = true; habitError.value = '';
      try {
        const response = await fetch('/api/v1/daily-habits');
        if (!response.ok) throw Error();
        habits.value = await response.json();
      } catch { habitError.value = 'Daily habits could not be loaded.'; }
      finally { habitsLoading.value = false; }
    }
    loadHabits();
    return { ...theme, ...library, ...daily, ...statistics, habits, habitError, habitsLoading, completedCount, savedCount, loadHabits };
  },
  template: `<div class="shell">
    <app-sidebar active="dashboard"/>
    <div class="content"><header><div class="breadcrumb">Your wellbeing <span>/</span><b>Dashboard</b></div><div class="topbar-tools"><label class="theme-picker"><span>Appearance</span><select :value="theme" @change="selectTheme($event.target.value)" aria-label="Color theme"><option v-for="item in themes" :key="item.id" :value="item.id">{{ item.label }}</option></select></label><profile-badge/></div></header>
    <main><div class="page-heading"><div class="eyebrow">YOUR DAILY WELLBEING</div><h1>A little better, every day<span>.</span></h1><p>Your breaks, movements, and habits. All in one place.</p></div>
    <section class="hero dashboard-hero" aria-labelledby="welcome-title"><div class="hero-copy"><span class="pill">✦ TODAY IS A FRESH START</span><h2 id="welcome-title">Make your next break<br>a good one.</h2><p>Change position. Find a comfortable stretch.<br>Build the little habits that fit your day.</p><a class="primary" href="/breaks.html">Take a break <span>↗</span></a></div><div class="hero-art"><div class="orbit"></div><div class="orbit orbit-two"></div><movement-figure kind="reach"/></div></section>
    <p class="home-muted" role="status">{{ activityNotice }}</p><button v-if="!activityReady && activityMode === 'unavailable'" class="secondary" @click="retryActivity">Retry activity storage</button>
    <section class="home-stats" aria-label="Your daily overview"><article><span>Breaks completed</span><strong>{{ activityReady ? completedBreaks : '—' }}</strong><small>{{ activityMode === 'account' ? 'Today, in your account' : 'Today, in this browser' }}</small></article><article><span>Daily habits</span><strong>{{ habitsLoading || habitError || !activityReady ? '—' : completedCount + ' / ' + habits.length }}</strong><small>{{ day }}</small></article><article><span>Movement library</span><strong>{{ loading || error ? '—' : exercises.length }}</strong><small>Movements to explore</small></article><article><span>Saved movements</span><strong>{{ loading || error ? '—' : savedCount }}</strong><small>Your personal collection</small></article></section>
    <section class="dashboard-statistics" aria-labelledby="statistics-title">
      <div class="home-section-heading"><div><div class="eyebrow">NOTICE YOUR PROGRESS</div><h2 id="statistics-title">Your statistics</h2></div><span class="statistics-period">Today · {{ day }}</span></div>
      <div class="statistics-grid">
        <article class="home-panel habit-statistics" aria-labelledby="habit-statistics-title"><h3 id="habit-statistics-title">Daily habit completion</h3>
          <p v-if="habitsLoading" role="status" class="home-muted">Loading habit statistics…</p>
          <div v-else-if="habitError" role="alert"><p class="home-muted">{{ habitError }}</p><button class="secondary" @click="loadHabits">Retry habits</button></div>
          <template v-else-if="activityReady"><div class="habit-donut" :style="{'--completion': habitCompletion + '%'}" role="img" :aria-label="habitCompletion + '% of today’s habits completed'"><div><strong>{{ habitCompletion }}%</strong><span>of daily habits</span></div></div><p class="home-muted">{{ completedCount }} of {{ habits.length }} habits checked today</p><div class="statistics-break-total"><strong>{{ activityReady ? completedBreaks : '—' }}</strong><span>Timed breaks completed today</span></div></template>
          <small class="statistics-note">{{ activityNotice }} Checkmarks represent self-reported habits.</small>
        </article>
        <article class="home-panel catalog-statistics" aria-labelledby="coverage-title"><h3 id="coverage-title">Movement library coverage</h3>
          <p v-if="loading" role="status" class="home-muted">Loading library statistics…</p>
          <div v-else-if="error" role="alert"><p class="home-muted">{{ error }}</p><button class="secondary" @click="load">Retry library</button></div>
          <template v-else><p class="home-muted">{{ catalogStatistics.coveredAreas }} of 6 body areas represented · {{ catalogStatistics.total }} movements</p><div class="coverage-chart" role="list" aria-label="Exercises by body area"><div v-for="item in catalogStatistics.coverage" :key="item.area" role="listitem" class="statistics-bar-row"><span>{{ item.area }}</span><meter :value="item.count" min="0" :max="Math.max(catalogStatistics.total,1)" :aria-label="item.area + ': ' + item.count + ' of ' + catalogStatistics.total + ' movements'"></meter><b>{{ item.count }}</b></div></div><div class="catalog-stat-cards"><div><strong>{{ catalogStatistics.quickBreaks }}</strong><span>Moves of 60 sec or less</span></div><div><strong>{{ catalogStatistics.averageSeconds }}<small>sec</small></strong><span>Average catalog duration</span></div><div><strong>{{ catalogStatistics.savedPercentage }}<small>%</small></strong><span>Of the library saved</span></div></div><p v-if="!catalogStatistics.total" class="home-muted">Your library is empty. Add movements through Administration to build coverage.</p></template>
          <small class="statistics-note">Catalog durations describe available exercises, not time you spent exercising.</small>
        </article>
      </div>
    </section>
    <div class="home-columns"><section class="home-panel" aria-labelledby="habits-title"><div class="home-section-heading"><h2 id="habits-title">Your daily habits</h2><a href="/breaks.html" class="text-button">View all →</a></div><p class="home-muted">Small actions, tied to everyday moments.</p><p v-if="habitsLoading" role="status">Loading today's habits…</p><div v-else-if="habitError" role="alert"><p>{{ habitError }}</p><button class="secondary" @click="loadHabits">Try again</button></div><template v-else><progress :max="Math.max(habits.length,1)" :value="completedCount" aria-label="Daily habit completion"></progress><div class="home-habits"><label v-for="habit in habits" :key="habit.id"><input type="checkbox" :disabled="!activityReady || savingActivity" :checked="completedHabits.includes(habit.id)" @change="toggleHabit(habit.id)"><span><b>{{ habit.name }}</b><small>{{ habit.cue }}</small></span></label></div><p v-if="habits.length && completedCount === habits.length" class="success" role="status">All your daily habits checked. Nicely done.</p></template><p v-if="storageWarning" role="status" class="home-muted">{{ storageWarning }}</p></section>
    <section class="home-panel" aria-labelledby="next-title"><h2 id="next-title">What feels right now?</h2><a class="home-action" href="/breaks.html"><span>01</span><div><h3>Find your reset</h3><p>Standard, comfort, strength, or movement-habit breaks.</p></div><b>↗</b></a><a class="home-action" href="/breaks.html#posture-title"><span>02</span><div><h3>Check your setup</h3><p>A quick self-check for desk work or phone use.</p></div><b>↗</b></a><a class="home-action" href="/library.html"><span>03</span><div><h3>Explore a movement</h3><p>Browse the library and save something for later.</p></div><b>↗</b></a><div class="home-note">{{ activityNotice }} No pressure to do it all.</div></section></div>
    <section class="home-panel home-library" aria-labelledby="explore-title"><div class="home-section-heading"><h2 id="explore-title">A little movement inspiration</h2><a class="text-button" href="/library.html">Explore library →</a></div><p v-if="loading" role="status">Loading movements…</p><div v-else-if="error" role="alert"><p>{{ error }}</p><button class="secondary" @click="load">Try again</button></div><p v-else-if="!exercises.length" class="home-muted">Your movement library is empty. An administrator can add movements.</p><div v-else class="home-movements"><a v-for="item in exercises.slice(0,3)" :key="item.id" href="/library.html" class="home-movement"><movement-figure :kind="item.symbol"/><span>{{ item.area }} · {{ item.duration }} sec</span><h3>{{ item.name }} ↗</h3><p>{{ item.description }}</p></a></div></section>
    <progress-panel :day="day" :mode="activityMode" :identity="activityIdentity" :habits="completedHabits" :breaks="completedBreaks" :ready="activityReady" :saving="savingActivity"/>
    <social-summary/>
    <footer><span>✳ Made for your everyday, not your personal best.</span><span>PosturePal v0.12.1</span></footer></main></div>
  </div>`
}).mount('#app');
