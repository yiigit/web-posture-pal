import { ref, computed, onUnmounted } from '/vendor/vue.esm-browser.prod.js';
export function useLibrary() {
  const exercises = ref([]), loading = ref(true), error = ref('');
  const query = ref(''), area = ref('All movements'), savedOnly = ref(false);
  let initial = [];
  try { initial = JSON.parse(localStorage.getItem('posturepal.favorites') || '[]'); } catch {}
  const favorites = ref(Array.isArray(initial) ? initial : []);
  const filtered = computed(() => exercises.value.filter(e =>
    (area.value === 'All movements' || e.area === area.value) &&
    (!savedOnly.value || favorites.value.includes(e.id)) &&
    `${e.name} ${e.area} ${e.description}`.toLowerCase().includes(query.value.toLowerCase())));
  function toggleFavorite(id) {
    favorites.value = favorites.value.includes(id) ? favorites.value.filter(x => x !== id) : [...favorites.value, id];
    try { localStorage.setItem('posturepal.favorites', JSON.stringify(favorites.value)); } catch {}
  }
  async function load() {
    loading.value = true; error.value = '';
    try { const r = await fetch('/api/v1/exercises'); if (!r.ok) throw Error(); exercises.value = await r.json(); }
    catch { error.value = 'We couldn’t load your movements. Please try again.'; }
    finally { loading.value = false; }
  }
  window.addEventListener('focus', load);
  onUnmounted(() => window.removeEventListener('focus', load));
  load();
  return { exercises, loading, error, query, area, savedOnly, favorites, filtered, toggleFavorite, load };
}
