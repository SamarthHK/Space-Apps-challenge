const byId = id => document.getElementById(id);

export function createAccountAccess(api, { onReady, onState, hasDraft }) {
  const panel = byId('account-access');
  const app = byId('app-container');
  const form = byId('account-form');
  const login = byId('account-login');
  const password = byId('account-password');
  const confirmation = byId('account-password-confirm');
  const status = byId('account-status');
  const submit = byId('account-submit');
  const toggle = byId('account-mode-toggle');
  const logout = byId('account-logout');
  const channel = 'BroadcastChannel' in window ? new BroadcastChannel('bhumi-account-session') : null;
  let session = null;
  let registering = new URL(window.location.href).searchParams.get('register') === '1';
  let checking = false;
  let busy = false;
  let ending = false;

  function render() {
    byId('account-title').textContent = registering ? 'Create your private workspace' : 'Welcome back to your land';
    submit.textContent = registering ? 'Create account' : 'Sign in';
    toggle.textContent = registering ? 'Already have an account? Sign in' : 'Create an account';
    password.autocomplete = registering ? 'new-password' : 'current-password';
    password.minLength = registering ? 12 : 1;
    confirmation.required = registering;
    byId('account-confirm-label').hidden = !registering;
    byId('account-fields').disabled = busy;
    submit.disabled = busy;
    toggle.disabled = busy;
    logout.hidden = !session?.user;
    logout.disabled = busy || checking;
    byId('retry-connection').disabled = checking;
  }
  function restart(reason, announce = false) {
    if (ending) return;
    ending = true;
    app.hidden = true;
    password.value = '';
    confirmation.value = '';
    api.setSession(null);
    if (announce) channel?.postMessage('changed');
    const url = new URL(window.location.href);
    url.search = '';
    url.hash = '';
    if (reason) url.searchParams.set('session', reason);
    window.location.replace(url);
  }
  if (channel) channel.onmessage = () => {
    if (session?.mode === 'accounts') restart('changed');
  };
  window.addEventListener('pagehide', () => {
    if (session?.user) app.hidden = true;
    password.value = '';
    confirmation.value = '';
    channel?.close();
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted && session?.mode === 'accounts') restart('changed');
  });

  async function readSession() {
    return (await api.get('/auth/session', { schema: 'SessionResponse' })).data;
  }
  async function discover() {
    try {
      return await readSession();
    } catch (error) {
      if (error.status !== 404) throw error;
      const health = await api.get('/health', { schema: 'HealthResponse' });
      if (health.data.contract_revision !== 'shared-workspace-1') throw error;
      return { mode: 'shared', user: null, csrf_token: null, expires_at: null };
    }
  }
  async function check() {
    if (checking || ending) return;
    checking = true;
    render();
    onState('Checking workspace access...', 'loading');
    try {
      let next = await discover();
      if (next.mode === 'accounts' && session?.mode !== 'accounts') {
        api.setSession({ userId: null, csrfToken: null });
        next = await readSession();
      } else if (next.mode === 'shared') api.setSession(null);
      if (ending) return;
      if (session && (session.mode !== next.mode || session.user?.id !== next.user?.id)) {
        restart(next.user ? 'changed' : 'expired');
        return;
      }
      session = next;
      if (next.mode === 'accounts' && !next.user) {
        panel.hidden = false;
        app.hidden = true;
        const reason = new URL(window.location.href).searchParams.get('session');
        status.textContent = reason === 'expired'
          ? 'Your session ended. Sign in again. Previous private data and unsaved browser edits were cleared.'
          : reason === 'changed' ? 'The signed-in account changed. Previous browser data was cleared.' : '';
        login.focus();
      } else {
        if (next.user) api.setSession({ userId: next.user.id, csrfToken: next.csrf_token });
        panel.hidden = true;
        app.hidden = false;
        await onReady(next);
      }
    } catch (error) {
      if (!ending) {
        app.hidden = false;
        panel.hidden = true;
        onState(error.message, 'error');
      }
    } finally {
      checking = false;
      render();
    }
  }

  toggle.addEventListener('click', () => {
    registering = !registering;
    password.value = '';
    confirmation.value = '';
    status.textContent = '';
    render();
    login.focus();
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || ending) return;
    if (registering && password.value !== confirmation.value) {
      status.textContent = 'The passwords do not match.';
      confirmation.focus();
      return;
    }
    busy = true;
    render();
    status.textContent = registering ? 'Creating your private workspace...' : 'Signing in...';
    const requestedLogin = login.value.trim().toLowerCase();
    try {
      const bootstrap = await api.request('/auth/bootstrap', { method: 'POST', schema: 'SignInContextResponse' });
      const response = await api.request(registering ? '/auth/register' : '/auth/login', {
        method: 'POST', body: { login: login.value, password: password.value },
        headers: { 'X-CSRF-Token': bootstrap.body.data.csrf_token }, schema: 'SessionResponse',
      });
      const verified = await readSession();
      if (!verified.user || verified.user.id !== response.body.data.user.id) {
        throw new Error('The browser did not retain this sign-in. Use the same hostname for the frontend and API, then sign in again.');
      }
      restart(null, true);
    } catch (error) {
      if (ending) return;
      if (error.outcomeUncertain) {
        let recovered;
        try { recovered = await readSession(); } catch { /* Keep the uncertain outcome explicit. */ }
        if (recovered?.user?.login === requestedLogin) {
          restart(null, true);
          return;
        }
        registering = false;
        status.textContent = 'The sign-in/registration outcome is unknown. Nothing was retried. '
          + 'Sign in with the same login and password to recover an account that may already exist.';
      } else {
        status.textContent = [error.message, ...(error.details ?? []).map(detail =>
          `${detail.path.replace(/^body\./, '')}: ${detail.message}`)].join(' ');
      }
    } finally {
      password.value = '';
      confirmation.value = '';
      busy = false;
      render();
    }
  });
  logout.addEventListener('click', async () => {
    if (busy || !session?.user) return;
    if (hasDraft() && !window.confirm(
      'Sign out and discard unsaved browser edits? Server jobs continue. Copy the current job URL first if you need to resume it.')) return;
    busy = true;
    render();
    try {
      await api.request('/auth/logout', { method: 'POST' });
      restart(null, true);
    } catch (error) {
      if (ending) return;
      try {
        if (!(await readSession()).user) { restart(null, true); return; }
      } catch { /* Revocation has not been confirmed. */ }
      onState(`${error.message} Sign-out is not confirmed; retry before leaving a shared browser.`, 'error');
    } finally {
      busy = false;
      render();
    }
  });
  render();
  return { check, end: reason => restart(reason === 'session_changed' ? 'changed' : 'expired') };
}
