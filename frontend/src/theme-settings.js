/* Apply the saved theme before styles load to avoid a light flash. */
(() => {
  const storageKey = 'posturepal.theme';
  const themes = Object.freeze([
    { id: 'light', label: 'Light' },
    { id: 'dark', label: 'Dark' },
    { id: 'sportive', label: 'Sportive' },
    { id: 'nike', label: 'Nike Orange' },
  ]);
  function apply(id) {
    const theme = themes.some(item => item.id === id) ? id : 'light';
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      'content', { light: '#285b49', dark: '#121b18', sportive: '#10252d', nike: '#ff5a00' }[theme]);
    return theme;
  }
  let saved;
  try { saved = localStorage.getItem(storageKey); } catch {}
  apply(saved);
  window.PosturePalTheme = Object.freeze({
    themes,
    select(id) {
      const theme = apply(id);
      try { localStorage.setItem(storageKey, theme); } catch {}
      return theme;
    },
  });
})();
