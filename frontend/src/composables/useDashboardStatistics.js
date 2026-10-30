import { computed } from '/vendor/vue.esm-browser.prod.js';

/** Derive catalog and daily statistics without inventing workout telemetry. */
export function useDashboardStatistics(exercises, habits, completedHabits, favorites) {
  const habitCompletion = computed(() => habits.value.length
    ? Math.round(100 * habits.value.filter(item => completedHabits.value.includes(item.id)).length / habits.value.length)
    : 0);
  const catalogStatistics = computed(() => {
    const items = exercises.value;
    const areas = ['Neck', 'Shoulders', 'Back', 'Wrists', 'Legs', 'Full body'];
    const coverage = areas.map(area => ({ area, count: items.filter(item => item.area === area).length }));
    const totalSeconds = items.reduce((sum, item) => sum + item.duration, 0);
    const saved = items.filter(item => favorites.value.includes(item.id)).length;
    return {
      total: items.length,
      averageSeconds: items.length ? Math.round(totalSeconds / items.length) : 0,
      quickBreaks: items.filter(item => item.duration <= 60).length,
      savedPercentage: items.length ? Math.round(saved * 100 / items.length) : 0,
      coveredAreas: coverage.filter(item => item.count > 0).length,
      coverage,
    };
  });
  return { habitCompletion, catalogStatistics };
}
