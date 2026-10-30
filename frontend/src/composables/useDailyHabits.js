import { ref, onUnmounted } from '/vendor/vue.esm-browser.prod.js';

// Calendar days use the browser's local time, including daylight-saving changes.
function localDay() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
}
export function useDailyHabits() {
  const day = ref(localDay()), completedHabits = ref([]), completedBreaks = ref(0), storageWarning = ref('');
  function load() {
    day.value = localDay();
    completedHabits.value = []; completedBreaks.value = 0;
    try {
      const saved = JSON.parse(localStorage.getItem('posturepal.daily') || '{}');
      if (saved.day === day.value) {
        completedHabits.value = Array.isArray(saved.habits) ? saved.habits.filter(x => typeof x === 'string') : [];
        completedBreaks.value = Number.isSafeInteger(saved.breaks) && saved.breaks >= 0 ? saved.breaks : 0;
      }
    } catch { storageWarning.value = 'Progress is available for this visit only; browser storage is unavailable.'; }
  }
  function rollover() { if (day.value !== localDay()) load(); }
  function persist() {
    try { localStorage.setItem('posturepal.daily', JSON.stringify({day: day.value, habits: completedHabits.value, breaks: completedBreaks.value})); }
    catch { storageWarning.value = 'Progress is available for this visit only; browser storage is unavailable.'; }
  }
  function toggleHabit(id) {
    rollover();
    completedHabits.value = completedHabits.value.includes(id) ? completedHabits.value.filter(x => x !== id) : [...completedHabits.value, id];
    persist();
  }
  function recordBreak() { rollover(); completedBreaks.value++; persist(); }
  function sync(event) { if (event.key === 'posturepal.daily') load(); }
  load();
  const timer = setInterval(rollover, 1000);
  window.addEventListener('storage', sync);
  window.addEventListener('focus', load);
  onUnmounted(() => { clearInterval(timer); window.removeEventListener('storage', sync); window.removeEventListener('focus', load); });
  return { day, completedHabits, completedBreaks, storageWarning, toggleHabit, recordBreak };
}
