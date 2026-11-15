import { profileFields, profileChanges } from '../api/profile.js';

const node = (tag, text) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  return element;
};

export function createProfile(container, api, { onChange = () => {} } = {}) {
  const status = node('p', 'Shared-profile storage is not connected.');
  status.id = 'profile-status';
  status.setAttribute('role', 'status');
  const errors = node('ul');
  errors.setAttribute('role', 'alert');
  const form = node('form');
  const controls = node('fieldset');
  controls.className = 'profile-form-grid';
  for (const [key, title, options, limit = 200] of profileFields) {
    const label = node('label', title);
    const input = node(options ? 'select' : 'input');
    input.id = `profile-${key}`;
    input.name = key;
    input.className = options ? 'form-select' : 'form-input';
    if (options) {
      input.append(new Option('Not specified', ''));
      options.forEach(([value, text]) => input.append(new Option(text, value)));
    } else input.maxLength = limit;
    label.append(input);
    controls.append(label);
  }
  const save = node('button', 'Save shared profile');
  save.className = 'btn-primary';
  save.type = 'submit';
  const reload = node('button', 'Reload (discards edits)');
  reload.className = 'btn-secondary';
  reload.type = 'button';
  form.append(controls, save, reload);
  container.append(status, errors, form);
  let available = false;
  let record = null;
  let etag = null;
  let busy = false;
  let dirty = false;
  let needsReload = false;
  let generation = 0;
  let privateAccount = false;
  const label = () => privateAccount ? 'Profile' : 'Shared profile';

  function renderButtons() {
    controls.disabled = !available || busy || !record;
    save.disabled = !available || busy || !dirty || needsReload || !etag;
    reload.disabled = !available || busy;
  }
  function apply(response) {
    if (!response.etag) throw new Error('The backend did not expose a profile ETag. Reload after fixing CORS.');
    record = response.body.data;
    etag = response.etag;
    profileFields.forEach(([key]) => { form.elements.namedItem(key).value = record[key] ?? ''; });
    dirty = false;
    needsReload = false;
    status.textContent = `${label()} version ${record.version}. ${privateAccount
      ? 'Saved in your private account.' : 'Visible to everyone with workspace access.'}`;
    onChange(record);
  }
  async function load() {
    if (!available || busy) return;
    const current = ++generation;
    busy = true;
    renderButtons();
    errors.replaceChildren();
    status.textContent = `Loading ${label().toLowerCase()}...`;
    try {
      const response = await api.request('/profile', { schema: 'ProfileResponse' });
      if (current === generation) apply(response);
    } catch (error) {
      if (current === generation) {
        status.textContent = `${error.message} Existing edits were retained.`;
        needsReload = true;
      }
    } finally {
      if (current === generation) { busy = false; renderButtons(); }
    }
  }
  form.addEventListener('input', () => {
    if (record) dirty = Object.keys(profileChanges(new FormData(form), record)).length > 0;
    renderButtons();
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (save.disabled) return;
    const body = profileChanges(new FormData(form), record);
    busy = true;
    renderButtons();
    errors.replaceChildren();
    status.textContent = `Saving ${label().toLowerCase()}...`;
    try {
      const response = await api.request('/profile', {
        method: 'PATCH', body, headers: { 'If-Match': etag }, schema: 'ProfileResponse',
      });
      apply(response);
      status.textContent = `Saved ${label().toLowerCase()} version ${record.version}.`;
    } catch (error) {
      needsReload = error.status === 412 || error.outcomeUncertain || !(error.status >= 400 && error.status < 500);
      status.textContent = `${error.message} Your edits were retained.${needsReload
        ? ' Reload before another save; the stored value may have changed.' : ''}`;
      (error.details ?? []).forEach(detail => errors.append(node('li', `${detail.path}: ${detail.message}`)));
    } finally {
      busy = false;
      renderButtons();
    }
  });
  reload.addEventListener('click', load);
  renderButtons();
  return {
    hasDraft: () => dirty || busy,
    setIdentity(user) {
      privateAccount = !!user;
      save.textContent = privateAccount ? 'Save profile' : 'Save shared profile';
      document.getElementById('profile-privacy-notice').textContent = privateAccount
        ? 'This profile is private to your signed-in account. Your declarations are not laboratory verification.'
        : 'This profile is shared in the current workspace mode. Only enter information intended to be shared; no private donor records are imported.';
    },
    setAvailable(value) {
      available = value;
      renderButtons();
      if (available && !record && !busy) load();
      if (!available && !busy) status.textContent = `${label()} storage is blocked or disconnected. Existing edits are retained.`;
    },
  };
}
