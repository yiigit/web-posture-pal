import { useAdminVisibility } from '../composables/useAdminVisibility.js';

/** Persistent shared navigation for every application page. */
export default {
  setup: useAdminVisibility,
  props: { active: { type: String, required: true } },
  template: `<aside class="sidebar">
    <a class="brand" href="/" aria-label="PosturePal home"><span class="brand-icon">ᴘ</span>Posture<span>Pal</span></a>
    <div class="workspace-label">YOUR WELLBEING SPACE</div>
    <nav aria-label="Main navigation">
      <a class="coach-link" :class="{'navigation-active': active === 'dashboard'}" href="/" :aria-current="active === 'dashboard' ? 'page' : undefined" aria-label="Dashboard">⌂ <span>Dashboard</span></a>
      <a class="coach-link" :class="{'navigation-active': active === 'library'}" href="/library.html" :aria-current="active === 'library' ? 'page' : undefined" aria-label="Movement library">▦ <span>Movement library</span></a>
      <a class="coach-link" :class="{'navigation-active': active === 'breaks'}" href="/breaks.html" :aria-current="active === 'breaks' ? 'page' : undefined" aria-label="Breaks and daily habits">↗ <span>Breaks & daily habits</span></a>
      <a class="coach-link" :class="{'navigation-active': active === 'social'}" :aria-current="active === 'social' ? 'page' : undefined" href="/social.html" aria-label="Friends and sharing">♧ <span>Friends & sharing</span></a>
      <slot/>
      <a class="coach-link" :class="{'navigation-active': active === 'account'}" :aria-current="active === 'account' ? 'page' : undefined" href="/account.html" aria-label="Your profile">◉ <span>Account & profile</span></a>
      <a v-if="isAdmin" class="coach-link" :class="{'navigation-active': active === 'users'}" :aria-current="active === 'users' ? 'page' : undefined" href="/users.html" aria-label="User management">♙ <span>User management</span></a>
    </nav>
    <div class="sidebar-note"><span class="little-flower">✳</span><h3>Small moves.<br>Better days.</h3><p>Make a little space for yourself, one break at a time.</p></div>
    <a v-if="isAdmin" class="coach-link" :class="{'navigation-active': active === 'admin'}" :aria-current="active === 'admin' ? 'page' : undefined" href="/admin.html" aria-label="Administration">⚙ <span>Administration</span></a>
  </aside>`,
};
