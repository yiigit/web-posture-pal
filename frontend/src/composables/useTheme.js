import { ref } from '/vendor/vue.esm-browser.prod.js';

export function useTheme() {
  const theme = ref(document.documentElement.dataset.theme || 'light');
  const themes = window.PosturePalTheme.themes;
  function selectTheme(id) {
    theme.value = window.PosturePalTheme.select(id);
  }
  return { theme, themes, selectTheme };
}
