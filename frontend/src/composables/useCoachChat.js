import { ref, onMounted, onUnmounted } from '/vendor/vue.esm-browser.prod.js';

export function useCoachChat() {
  const user = ref(null), context = ref(null), enabled = ref(false), loading = ref(true);
  const messages = ref([]), draft = ref(''), consent = ref(false), busy = ref(false), error = ref('');
  let revision = 0, identityRevision = 0, controller, timer;
  const day = () => { const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`; };
  function clearChat() {
    ++revision;
    controller?.abort();
    messages.value = []; draft.value = ''; consent.value = false; busy.value = false; error.value = '';
  }
  async function request(path, options = {}) {
    const response = await fetch('/api/v1' + path, { credentials: 'same-origin', cache: 'no-store', ...options });
    if (!response.ok) {
      if ([401,409].includes(response.status)) {
        clearChat(); user.value = null; context.value = null; enabled.value = false;
      }
      const data = await response.json().catch(() => ({}));
      throw Error(typeof data.detail === 'string' ? data.detail : 'Unable to load chat. Please try again.');
    }
    return response.json();
  }
  async function refresh() {
    const current = ++identityRevision;
    try {
      const response = await fetch('/api/v1/users/me', { credentials: 'same-origin', cache: 'no-store' });
      const next = response.ok ? await response.json() : null;
      if (current !== identityRevision) return;
      if (next?.id !== user.value?.id) clearChat();
      user.value = next;
      if (!next) { context.value = null; enabled.value = false; return; }
      const snapshot = await request('/me/coach/context?day=' + day(), { headers: {'X-PosturePal-User': next.id} });
      if (current !== identityRevision || user.value?.id !== next.id) return;
      context.value = snapshot.context; enabled.value = snapshot.enabled;
    } catch {
      if (current !== identityRevision) return;
      clearChat(); user.value = null; context.value = null; enabled.value = false;
      error.value = 'Could not verify your account. Chat paused; please try again.';
    } finally { if (current === identityRevision) loading.value = false; }
  }
  async function send() {
    if (busy.value || !user.value || !enabled.value || !consent.value || !draft.value.trim()) return;
    if (messages.value.length >= 10) { error.value = 'This chat is full. Clear it to start a new conversation.'; return; }
    const message = { role: 'user', content: draft.value.trim() };
    const history = [...messages.value, message];
    if (message.content.length > 2000 || history.reduce((sum, item) => sum + item.content.length, 0) > 12000) {
      error.value = 'This message or chat is too long. Shorten it or clear the chat.'; return;
    }
    busy.value = true; error.value = '';
    const current = revision, owner = user.value.id;
    controller = new AbortController();
    try {
      const result = await request('/me/coach/messages', {
        method: 'POST', signal: controller.signal,
        headers: {'Content-Type':'application/json', 'X-PosturePal-Request':'1', 'X-PosturePal-User':owner},
        body: JSON.stringify({day:day(), consent:true, messages:history}),
      });
      if (current !== revision || user.value?.id !== owner) return;
      messages.value = [...history, {role:'assistant', content:result.reply}];
      draft.value = '';
    } catch (failure) {
      if (current === revision && failure.name !== 'AbortError') error.value = failure.message;
    } finally { if (current === revision) busy.value = false; }
  }
  function changed() { ++identityRevision; clearChat(); user.value = null; context.value = null; enabled.value = false; refresh(); }
  function storage(event) { if (event.key === 'posturepal.auth.changed' || event.key === null) changed(); }
  function visible() { if (!document.hidden) refresh(); }
  onMounted(() => {
    refresh(); timer = setInterval(visible,15000);
    window.addEventListener('focus', refresh);
    window.addEventListener('posturepal:account-changed', changed);
    window.addEventListener('storage', storage);
    document.addEventListener('visibilitychange', visible);
  });
  onUnmounted(() => {
    ++identityRevision; clearChat(); clearInterval(timer);
    window.removeEventListener('focus', refresh);
    window.removeEventListener('posturepal:account-changed', changed);
    window.removeEventListener('storage', storage);
    document.removeEventListener('visibilitychange', visible);
  });
  return {user,context,enabled,loading,messages,draft,consent,busy,error,refresh,send,clearChat};
}
