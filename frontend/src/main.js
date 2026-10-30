import AppSidebar from './components/AppSidebar.js';
import ProfileBadge from './components/ProfileBadge.js';
import { createApp, ref, computed, onUnmounted, watch } from '/vendor/vue.esm-browser.prod.js';
import { useLibrary } from './composables/useLibrary.js';
import { useTheme } from './composables/useTheme.js';
import MovementFigure from './components/MovementFigure.js';
createApp({
 components: { AppSidebar, ProfileBadge, MovementFigure },
 setup() {
  const library = useLibrary();
  const theming = useTheme();
  const selected = ref(null), remaining = ref(0), running = ref(false), completed = ref(false);
  const areas = computed(() => ['All movements', ...new Set(library.exercises.value.map(e => e.area))]);
  let timer;
  function pause() { clearInterval(timer); running.value = false; }
  function open(e) { pause(); selected.value = e; remaining.value = e.duration; completed.value = false; }
  function close() { pause(); selected.value = null; }
  function start() { if (running.value) return; running.value = true; timer = setInterval(() => { if (remaining.value > 0) remaining.value--; if (remaining.value === 0) { pause(); completed.value = true; } }, 1000); }
  function reset() { pause(); remaining.value = selected.value.duration; completed.value = false; }
  const time = computed(() => `${Math.floor(remaining.value / 60)}:${String(remaining.value % 60).padStart(2, '0')}`);
  function escape(e) { if (e.key === 'Escape') close(); }
  window.addEventListener('keydown', escape);
  watch(selected, value => { document.body.style.overflow = value ? 'hidden' : ''; if (value) setTimeout(() => document.querySelector('.close')?.focus(), 0); else document.querySelector('main h1')?.focus(); });
  function trap(e) { if(e.key !== 'Tab') return; const buttons = [...e.currentTarget.querySelectorAll('button')]; const first = buttons[0], last = buttons.at(-1); if(e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); } else if(!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); } }
  onUnmounted(() => { pause(); window.removeEventListener('keydown', escape); });
  return { ...library, ...theming, selected, remaining, running, completed, areas, open, close, start, pause, reset, time, trap };
 },
 template: `
 <div class="shell">
  <app-sidebar active="library"><button :class="{active: savedOnly}" @click="savedOnly = !savedOnly" :aria-pressed="savedOnly" aria-label="Show saved movements">♡ <span>Saved movements</span><small>{{ favorites.length }}</small></button></app-sidebar>
  <div class="content"><header><div class="breadcrumb">Your wellbeing <span>/</span> <b>Movement library</b></div><div class="header-actions"><label class="theme-picker"><span>Appearance</span><select :value="theme" @change="selectTheme($event.target.value)" aria-label="Color theme"><option v-for="item in themes" :key="item.id" :value="item.id">{{ item.label }}</option></select></label><profile-badge/></div></header>
   <main><div class="page-heading"><div class="eyebrow">MOVE WELL, FEEL WELL</div><h1 tabindex="-1">Your next feel-good move<span>.</span></h1><p>Small breaks. Gentle stretches. A happier you at your desk.</p></div>
   <section class="hero" aria-labelledby="hero-title"><div class="hero-copy"><span class="pill">✦ YOUR DAILY RESET</span><h2 id="hero-title">Less sitting still.<br>More feeling good.</h2><p>You don't need a gym or a spare hour.<br>Just a little space and a moment for yourself.</p><button class="primary" @click="exercises.length && open(exercises.find(e => e.id === 'standing-reach') || exercises[0])" :disabled="!exercises.length">Take a movement break <span>↗</span></button><small>NO EQUIPMENT. NO PRESSURE. JUST YOU.</small></div><div class="hero-art"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><span class="art-star">✳</span><movement-figure kind="reach"/><span class="floating-label">↗ &nbsp; A little stretch, a big difference</span></div></section>
   <section class="library" aria-labelledby="library-title"><div class="section-heading"><div><h2 id="library-title">{{ savedOnly ? 'Your saved movements' : 'Movement & exercise library' }}</h2><p>Find a movement that meets you where you are.</p></div><span class="count">{{ exercises.length }} simple ways to reset</span></div>
   <div class="toolbar"><div class="tabs" aria-label="Body area"><button v-for="item in areas" :key="item" :class="{selected: area === item}" :aria-pressed="area === item" @click="area = item">{{ item }}</button></div><label class="search"><span>⌕</span><input v-model="query" type="search" aria-label="Search movements" placeholder="Search movements..."></label></div>
   <div v-if="loading" class="empty" role="status">Finding your next movement…</div><div v-else-if="error" class="empty" role="alert">{{ error }} <button @click="load">Try again</button></div><div v-else-if="!filtered.length" class="empty"><h3>No movements here yet</h3><p>Try another search or body area, or save a movement with the heart button.</p><button @click="query = ''; area = 'All movements'; savedOnly = false">Explore all movements</button></div>
   <div v-else class="exercise-grid"><article v-for="(e,index) in filtered" :key="e.id" class="exercise-card"><div class="card-art" :class="e.symbol"><span class="area-tag">{{ e.area }}</span><button class="favorite" :class="{saved: favorites.includes(e.id)}" :aria-label="(favorites.includes(e.id) ? 'Unsave ' : 'Save ') + e.name" :aria-pressed="favorites.includes(e.id)" @click="toggleFavorite(e.id)">{{ favorites.includes(e.id) ? '♥' : '♡' }}</button><movement-figure :kind="e.symbol"/></div><div class="card-body"><div class="metadata"><span>◷ {{ e.duration < 60 ? e.duration + ' sec' : e.duration / 60 + ' min' }}</span><span>·</span><span>Gentle</span><span class="position">{{ e.position }}</span></div><h3><button @click="open(e)">{{ e.name }}<span>↗</span></button></h3><p>{{ e.description }}</p><button class="text-button" @click="open(e)">Let's move <span>→</span></button></div></article></div>
   </section><footer><span>✳ Made for your everyday, not your personal best.</span><span><a href="/admin.html">Manage library</a> · PosturePal <small>v0.10.0</small></span></footer>
   </main></div>
  <div v-if="selected" class="modal-overlay" @click.self="close"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="exercise-title" @keydown="trap"><button class="close" @click="close" aria-label="Close exercise">×</button><div class="modal-art" :class="selected.symbol"><movement-figure :kind="selected.symbol"/></div><div class="modal-content"><div class="eyebrow">{{ selected.area }} · {{ selected.position }}</div><h2 id="exercise-title">{{ selected.name }}</h2><p>{{ selected.description }}</p><ol><li v-for="step in selected.steps" :key="step">{{ step }}</li></ol><div class="timer" role="timer" aria-label="Time remaining">{{ time }}</div><p v-if="completed" class="success" role="status">Nicely done. A little movement counts.</p><div class="timer-actions"><button v-if="!completed" class="primary" @click="running ? pause() : start()">{{ running ? 'Pause break' : remaining === selected.duration ? 'Start break' : 'Resume break' }}</button><button v-else class="primary" @click="close">Feeling good · Done ✓</button><button class="secondary" @click="reset">Reset</button></div><p class="care-note">Keep movements gentle and comfortable. Stop if you feel pain.</p></div></section></div>
 </div>`
}).mount('#app');
