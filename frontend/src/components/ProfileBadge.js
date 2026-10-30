import { ref, computed, onMounted, onUnmounted } from '/vendor/vue.esm-browser.prod.js';

export default {
  setup() {
    const user = ref(null), loading = ref(true), unavailable = ref(false);
    let controller;
    const initials = computed(() => user.value?.display_name.trim().split(/\s+/).slice(0, 2).map(part => Array.from(part)[0]).join('').toUpperCase() || 'P');
    async function refresh() {
      controller?.abort();
      controller = new AbortController();
      try {
        const response = await fetch('/api/v1/users/me', {credentials:'same-origin', cache:'no-store', signal:controller.signal});
        if (response.status === 401) { user.value = null; unavailable.value = false; }
        else if (response.ok) { user.value = await response.json(); unavailable.value = false; }
        else { unavailable.value = true; }
      } catch(error) { if (error.name !== 'AbortError') unavailable.value = true; }
      finally { loading.value = false; }
    }
    onMounted(() => {
      refresh();
      window.addEventListener('focus', refresh);
      window.addEventListener('posturepal:account-changed', refresh);
    });
    onUnmounted(() => {
      controller?.abort();
      window.removeEventListener('focus', refresh);
      window.removeEventListener('posturepal:account-changed', refresh);
    });
    return { user, loading, unavailable, initials };
  },
  template: `<div class="profile-badge-wrap">
    <span v-if="loading" class="profile-badge-loading" role="status">Loading profile…</span>
    <a v-else class="profile-badge" href="/account.html" :aria-label="user && !unavailable ? 'Open profile for ' + user.display_name : unavailable ? 'Open account — profile unavailable' : 'Sign in or create an account'" :title="user && !unavailable ? user.display_name : 'Account & profile'">
      <span class="profile-badge-avatar" aria-hidden="true">{{ user && !unavailable ? initials : '◉' }}</span>
      <span class="profile-badge-details"><b>{{ unavailable ? 'Account' : user ? user.display_name : 'Sign in' }}</b><small>{{ unavailable ? 'Profile unavailable' : user ? user.role === 'admin' ? 'Administrator' : 'Your profile' : 'Create an account' }}</small></span>
      <span class="profile-badge-arrow" aria-hidden="true">↗</span>
    </a>
  </div>`,
};
