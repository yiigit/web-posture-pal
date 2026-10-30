export async function accountApi(path, method = 'GET', data, token = '') {
  const response = await fetch('/api/v1' + path, {
    method, credentials: 'same-origin', cache: 'no-store',
    headers: {'X-PosturePal-Request':'1', ...(data ? {'Content-Type':'application/json'} : {}), ...(token ? {Authorization:`Bearer ${token}`} : {})},
    ...(data ? {body:JSON.stringify(data)} : {}),
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw Error(Array.isArray(result.detail) ? result.detail.map(e => `${e.loc.slice(1).join('.')}: ${e.msg}`).join('; ') : result.detail || 'Request failed');
  }
  if (method !== 'GET' && (path.startsWith('/auth/') || path.startsWith('/users/me'))) {
    window.dispatchEvent(new Event('posturepal:account-changed'));
    try { localStorage.setItem('posturepal.auth.changed',String(Date.now())); } catch {}
  }
  return response.status === 204 ? null : response.json();
}
