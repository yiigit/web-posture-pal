import { createApp } from '/vendor/vue.esm-browser.prod.js';
import AppSidebar from './components/AppSidebar.js';
import ProfileBadge from './components/ProfileBadge.js';
import { useCoachChat } from './composables/useCoachChat.js';

createApp({
  components: { AppSidebar, ProfileBadge },
  setup: useCoachChat,
  template: `<div class="shell"><app-sidebar active="coach"/><div class="content"><main class="admin-page coach-page">
    <div class="account-topbar"><a href="/" class="text-button">PosturePal dashboard</a><profile-badge/></div>
    <div class="admin-heading"><div><div class="eyebrow">A LITTLE ENCOURAGEMENT</div><h1>Your AI coach.</h1><p>Reflect on your habits, celebrate progress, and find a manageable next step.</p></div></div>
    <p v-if="loading" role="status">Checking your account…</p>
    <p v-if="error" class="admin-error" role="alert">{{error}} <button class="text-button" @click="refresh">Check connection</button></p>
    <section v-if="!loading && !user" class="admin-panel"><h2>Make it personal</h2><p>Sign in to chat about your private account activity and achievements. Browser-local guest activity stays on this device.</p><a href="/account.html" class="primary">Sign in to continue</a></section>
    <template v-if="user && context">
      <section class="admin-panel coach-summary"><div><span class="eyebrow">YOUR RETAINED PROGRESS</span><h2>{{context.profile.display_name}}</h2><p>{{context.progress.totals.active_days}} active days · {{context.progress.totals.breaks}} breaks · Level {{context.progress.level}}</p><small>Self-reported activity within the rolling {{context.progress.window_days}}-day window.</small></div><a href="/breaks.html" class="text-button">Keep moving →</a></section>
      <section class="admin-panel coach-consent"><h2>You choose what to share</h2><p>When you send a message, OpenAI receives your display name, time zone, retained activity totals, points, level, achievements, last seven days of activity, and this conversation. Email, bio, friends, passwords and guest activity are excluded.</p><p>Chat is kept in this page's memory only. Clearing it or leaving the page removes our copy. Provider retention policies may still apply; clearing chat cannot retract requests already sent. <a href="/privacy.html">Read the privacy details</a>.</p>
        <details><summary>Review the account context sent with messages</summary><pre>{{JSON.stringify(context,null,2)}}</pre></details>
        <p v-if="!enabled" role="status">AI chat is not configured yet. An administrator must set the server API key and model.</p>
        <label v-else class="coach-consent-check"><input type="checkbox" v-model="consent" @change="!consent && clearChat()">I agree to send this context and my messages to OpenAI for this chat.</label>
      </section>
      <section class="admin-panel coach-conversation" aria-label="AI coach conversation">
        <div class="coach-chat-heading"><h2>Let’s talk</h2><button class="secondary" @click="clearChat">Clear chat</button></div>
        <div class="coach-starters" v-if="!messages.length"><button class="secondary" @click="draft='What progress have I made?'">My progress</button><button class="secondary" @click="draft='Which achievement could I work toward next?'">My achievements</button><button class="secondary" @click="draft='Help me find motivation for one small action today.'">A little motivation</button></div>
        <div role="log" aria-label="Chat messages" aria-live="polite" aria-relevant="additions" class="coach-messages"><article v-for="(message,index) in messages" :key="index" class="coach-message" :class="message.role"><b>{{message.role==='user'?'You':'PosturePal AI'}}</b><p>{{message.content}}</p></article></div>
        <p v-if="busy" role="status">Your coach is thinking…</p>
        <form @submit.prevent="send"><label for="coach-message">Your message</label><textarea id="coach-message" v-model="draft" maxlength="2000" rows="3" :disabled="busy || !enabled || !consent" placeholder="Ask about your progress or a small next step…" required></textarea><div class="coach-chat-heading"><small>AI can make mistakes. General habit guidance, not medical advice.</small><button class="primary" :disabled="busy || !enabled || !consent || !draft.trim()">Send message</button></div></form>
      </section>
    </template>
  </main></div></div>`,
}).mount('#app');
