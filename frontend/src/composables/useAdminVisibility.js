import { ref, onMounted, onUnmounted } from '/vendor/vue.esm-browser.prod.js';

/** Navigation reflects the current cookie session, never a stored role or admin token. */
export function useAdminVisibility() {
  const isAdmin = ref(false);
  let controller, revision = 0, timer;
  async function refresh() {
    const current = ++revision;
    controller?.abort();
    controller = new AbortController();
    isAdmin.value = false;
    try {
      const response = await fetch('/api/v1/users/me', {
        credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
      });
      const user = response.ok ? await response.json() : null;
      if (current === revision) isAdmin.value = user?.role === 'admin' && Boolean(user.active);
    } catch {
      if (current === revision) isAdmin.value = false;
    }
  }
  function storage(event) {
    if (event.key === 'posturepal.auth.changed' || event.key === null) refresh();
  }
  function visibleRefresh() { if (!document.hidden) refresh(); }
  onMounted(() => {
    refresh();
    window.addEventListener('focus', refresh);
    window.addEventListener('posturepal:account-changed', refresh);
    window.addEventListener('storage', storage);
    document.addEventListener('visibilitychange', visibleRefresh);
    timer = setInterval(visibleRefresh, 15000);
  });
  onUnmounted(() => {
    ++revision;
    controller?.abort();
    clearInterval(timer);
    window.removeEventListener('focus', refresh);
    window.removeEventListener('posturepal:account-changed', refresh);
    window.removeEventListener('storage', storage);
    document.removeEventListener('visibilitychange', visibleRefresh);
  });
  return { isAdmin };
}
