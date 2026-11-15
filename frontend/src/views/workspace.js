import { createClient } from '../api/client.js';
import { validateResponse } from '../api/validation.js';
import { createResource } from '../state/resource.js';
import { createFieldMap } from '../map/fieldMap.js';
import { createProfile } from './profile.js';
import { createLandActions } from './landActions.js';
import { createAccountAccess } from './accountAccess.js';

const byId = id => document.getElementById(id);
const node = (tag, text) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  return element;
};
const message = error => `${error.message}${error.requestId ? ` (Request ${error.requestId})` : ''}`;
const encode = encodeURIComponent;
const display = value => value === null || value === undefined ? 'Unavailable' : String(value);

export function startWorkspace(origin) {
  const fieldMap = createFieldMap(byId('api-map'), byId('tile-status'));
  function showView(name) {
    document.querySelectorAll('[data-view]').forEach(tab => {
      const active = tab.dataset.view === name;
      tab.classList.toggle('active', active);
      if (active) tab.setAttribute('aria-current', 'page');
      else tab.removeAttribute('aria-current');
    });
    document.querySelectorAll('.view-section').forEach(section => {
      section.classList.toggle('active', section.id === `view-${name}`);
    });
    if (name === 'myland') fieldMap.show();
  }
  document.querySelectorAll('[data-view], [data-open-view]').forEach(button =>
    button.addEventListener('click', () => showView(button.dataset.view ?? button.dataset.openView)));
  byId('map-basemap').addEventListener('change', event => fieldMap.setBasemap(event.target.value));
  byId('btn-world-view').addEventListener('click', () => fieldMap.world());
  byId('btn-fit-parcel').addEventListener('click', () => fieldMap.fit());
  function revealTools() {
    byId('land-cockpit').classList.remove('tools-hidden');
    byId('toggle-plot-tools').setAttribute('aria-expanded', 'true');
  }
  byId('toggle-plot-tools').addEventListener('click', () => {
    const hidden = byId('land-cockpit').classList.toggle('tools-hidden');
    byId('toggle-plot-tools').setAttribute('aria-expanded', String(!hidden));
  });
  byId('btn-toggle-drawer').addEventListener('click', () => {
    const collapsed = byId('cockpit-bottom-drawer').classList.toggle('collapsed');
    byId('map-history').hidden = collapsed;
    byId('btn-toggle-drawer').setAttribute('aria-expanded', String(!collapsed));
    byId('api-map').parentElement.classList.toggle('history-open', !collapsed);
  });
  let api;
  let access;
  let currentSession = null;
  let profileName = null;
  try {
    api = createClient(origin, { validate: validateResponse, onSessionLost: reason => access?.end(reason) });
  } catch (error) {
    byId('connection-status').textContent = `Configuration error: ${error.message}`;
    byId('retry-connection').disabled = true;
    return;
  }
  const profile = createProfile(byId('shared-profile'), api, {
    onChange(record) {
      profileName = record.name;
      byId('header-farmer-name').textContent = record.name || currentSession?.user?.login || 'Workspace profile';
    },
  });
  let fields = [];
  let fieldId = null;
  let fieldsCursor = null;
  let observationCursors = [null];
  let pageIndex = 0;
  let nextObservationCursor = null;
  let selectedObservationId = null;
  let evidenceCursor = null;
  let filters = {};
  let canReadObservations = false;
  let bootGeneration = 0;
  let fieldEditing = false;
  let selectedHasBoundaries = false;
  const landActions = createLandActions(byId('land-actions'), api, fieldMap, {
    refresh: refreshFields,
    revealTools,
    lockSelection(value) {
      fieldEditing = value;
      byId('global-plot-select').disabled = value || !fields.length;
      byId('boundary-select').disabled = value || !fieldId || !selectedHasBoundaries;
      document.querySelectorAll('.saved-plot-button').forEach(button => { button.disabled = value; });
    },
  });
  for (const id of ['btn-start-drawing', 'btn-dash-add-plot', 'act-draw-plot']) {
    byId(id).addEventListener('click', () => { showView('myland'); landActions.startDrawing(); });
  }
  for (const id of ['btn-upload-boundary', 'btn-dash-import']) {
    byId(id).addEventListener('click', () => { showView('myland'); landActions.openImport(); });
  }
  byId('btn-export-kml').addEventListener('click', () => landActions.export('kml'));
  byId('btn-export-current-geojson').addEventListener('click', () => landActions.export('geojson'));

  const evidence = createResource(state => {
    byId('next-evidence').hidden = true;
    byId('evidence-details').textContent = '';
    if (state.status === 'loading') byId('evidence-status').textContent = 'Loading source evidence...';
    else if (state.status === 'error') byId('evidence-status').textContent = message(state.error);
    else if (state.status === 'ready' || state.status === 'empty') {
      byId('evidence-status').textContent = 'Stored observation and evidence page. Original units and time standards are retained.';
      byId('evidence-details').textContent = JSON.stringify(state.data.data, null, 2);
      evidenceCursor = state.data.data.evidence.meta.next_cursor;
      byId('next-evidence').hidden = !evidenceCursor;
    } else byId('evidence-status').textContent = 'Choose an observation\'s evidence.';
  });
  async function inspect(id, cursor = null) {
    selectedObservationId = id;
    const selectedField = fieldId;
    return evidence.load(`${selectedField}/${id}/${cursor}`, async signal => {
      const base = `/fields/${encode(selectedField)}/observations/${encode(id)}`;
      const [observation, records] = await Promise.all([
        api.get(base, { signal, schema: 'ObservationResponse' }),
        api.get(`${base}/evidence`, { signal, schema: 'EvidenceResponse', params: { cursor } }),
      ]);
      return { data: { observation: observation.data, evidence: records } };
    });
  }
  const observations = createResource(state => {
    byId('observations-body').replaceChildren();
    byId('previous-observations').disabled = true;
    byId('next-observations').disabled = true;
    nextObservationCursor = null;
    if (state.status === 'loading') byId('observations-status').textContent = 'Loading canonical observations...';
    else if (state.status === 'error') byId('observations-status').textContent = `${message(state.error)} Apply filters to restart.`;
    else if (state.status === 'ready' || state.status === 'empty') {
      const rows = state.data.data;
      byId('observations-status').textContent = rows.length
        ? `Page ${pageIndex + 1}: ${rows.length} source records. Not a complete total; no scientific approval implied.`
        : 'No matching observations. This does not establish scientific suitability.';
      rows.forEach(record => {
        const scientific = record.scientific_record;
        const value = ['value_numeric', 'value_text', 'value_boolean', 'value_date', 'value_geometry', 'value_series_ref']
          .map(key => scientific[key]).find(value => value !== null && value !== undefined);
        const row = node('tr');
        const values = [record.variable_id, typeof value === 'object' ? JSON.stringify(value) : display(value),
          `${display(scientific.standardized_unit)} / ${display(scientific.measurement_basis)}`,
          `${display(scientific.observed_at ?? scientific.period_start)} (${display(scientific.timezone)})`,
          `${record.validation_status}${record.has_conflicting_revisions ? ' - conflicting revisions' : ''}`];
        values.forEach(value => row.append(node('td', value)));
        const cell = node('td');
        const button = node('button', `Evidence (${record.evidence_count})`);
        button.className = 'btn-secondary';
        button.addEventListener('click', () => inspect(record.canonical_observation_id));
        cell.append(node('span', `${display(scientific.source_id)} / ${display(scientific.evidence_type)} `), button);
        row.append(cell);
        byId('observations-body').append(row);
      });
      nextObservationCursor = state.data.meta.next_cursor;
      byId('previous-observations').disabled = pageIndex === 0;
      byId('next-observations').disabled = !nextObservationCursor;
    } else byId('observations-status').textContent = 'Select a field.';
  });
  async function loadObservations() {
    evidence.clear();
    selectedObservationId = null;
    if (!fieldId || !canReadObservations) {
      observations.clear();
      byId('observations-status').textContent = 'Observation access is unavailable or no field is selected.';
      return;
    }
    const selected = fieldId;
    const params = { ...filters, cursor: observationCursors[pageIndex], limit: 50 };
    return observations.load(JSON.stringify([selected, params]), signal =>
      api.get(`/fields/${encode(selected)}/observations`, { signal, params, schema: 'ObservationsResponse' }));
  }
  const field = createResource(state => {
    selectedHasBoundaries = false;
    landActions.setField(null, null);
    byId('field-details').replaceChildren();
    byId('plot-summary-name').textContent = 'No plot selected';
    byId('plot-storage-status').textContent = 'No selection';
    byId('plot-summary-area').textContent = 'Select or draw a boundary';
    byId('dash-metric-area').textContent = '--';
    byId('dash-area-hint').textContent = 'Select a recorded boundary';
    byId('dash-metric-boundaries').textContent = '--';
    byId('btn-fit-parcel').disabled = true;
    fieldMap.setGeometry(null);
    byId('boundary-select').disabled = true;
    if (state.status === 'loading') byId('field-status').textContent = 'Loading stored field...';
    else if (state.status === 'error') byId('field-status').textContent = message(state.error);
    else if (state.status === 'ready') {
      const record = state.data.data;
      selectedHasBoundaries = !!record.boundary_versions.length;
      landActions.setField(record, state.data.etag);
      byId('plot-summary-name').textContent = record.name ?? record.field_id;
      byId('plot-storage-status').textContent = record.geometry ? 'Backend saved' : 'Choose version';
      const area = record.area_ha === null ? 'Choose a boundary version'
        : `${record.area_ha.toLocaleString(undefined, { maximumFractionDigits: 3 })} ha`;
      byId('plot-summary-area').textContent = area;
      byId('dash-metric-area').textContent = record.area_ha === null ? '--' : area;
      byId('dash-area-hint').textContent = record.area_m2 === null ? 'Select a recorded boundary'
        : `${record.area_m2.toLocaleString(undefined, { maximumFractionDigits: 2 })} m2 - backend measurement`;
      byId('dash-metric-boundaries').textContent = record.boundary_versions.length;
      byId('btn-fit-parcel').disabled = !record.geometry;
      const select = byId('boundary-select');
      select.replaceChildren(new Option('Select a recorded boundary version', ''));
      record.boundary_versions.forEach(version => select.add(new Option(version.boundary_id, version.boundary_id)));
      select.value = record.selected_boundary_id ?? '';
      select.disabled = fieldEditing || !record.boundary_versions.length;
      byId('field-status').textContent = record.geometry_status === 'selection_required'
        ? 'Multiple versions exist. Select one explicitly; no current boundary is assumed.'
        : record.geometry_status === 'available' ? 'Stored boundary loaded.' : 'No stored geometry is available.';
      for (const [label, value] of [
        ['Field', record.name ?? record.field_id], ['Project', record.project_id],
        ['Selected boundary', record.selected_boundary_id], ['Area (ha)', record.area_ha],
        ['Area (m2)', record.area_m2], ['Perimeter (m)', record.perimeter_m],
        ['Metric CRS', record.metric_crs], ['Repair notes', record.repair_notes],
      ]) byId('field-details').append(node('dt', label), node('dd', display(value)));
      fieldMap.setGeometry(record.geometry);
    } else byId('field-status').textContent = 'Select a field.';
  });
  async function selectField(id) {
    fieldId = id || null;
    observations.clear();
    evidence.clear();
    observationCursors = [null];
    pageIndex = 0;
    if (!fieldId) { field.clear(); return; }
    const selected = fieldId;
    await Promise.all([
      field.load(selected, signal => readField(selected, {}, signal)),
      loadObservations(),
    ]);
  }
  const fieldList = createResource(state => {
    byId('more-fields').hidden = true;
    if (state.status === 'loading') byId('fields-status').textContent = 'Loading fields...';
    else if (state.status === 'error') byId('fields-status').textContent = `${message(state.error)} Reconnect to restart.`;
    else if (state.status === 'ready' || state.status === 'empty') {
      fields = [...new Map([...fields, ...state.data.data].map(record => [record.field_id, record])).values()];
      fieldsCursor = state.data.meta.next_cursor;
      const select = byId('global-plot-select');
      select.replaceChildren(new Option('Select a field', ''));
      fields.forEach(record => select.add(new Option(record.name ?? record.field_id, record.field_id)));
      select.value = fieldId ?? '';
      select.disabled = fieldEditing || !fields.length;
      byId('fields-status').textContent = fields.length
        ? `${fields.length} fields loaded${fieldsCursor ? ' (more available)' : ''}. Area totals unavailable without explicit boundary selection.`
        : currentSession?.user ? 'No saved plots yet. Draw or import your first boundary.'
          : 'No fields in the configured shared projects.';
      byId('more-fields').hidden = !fieldsCursor;
      byId('dash-metric-plots').textContent = `${fields.length}${fieldsCursor ? '+' : ''}`;
      byId('dash-plots-hint').textContent = fieldsCursor ? 'More plots available' : 'Saved in your workspace';
      byId('dashboard-plots').replaceChildren();
      fields.forEach(record => {
        const button = node('button');
        button.className = 'saved-plot-button';
        button.disabled = fieldEditing;
        const label = node('span');
        label.append(node('strong', record.name ?? record.field_id),
          node('small', `${record.boundary_versions.length} boundary versions - ${record.geometry_status === 'available'
            ? 'stored geometry' : 'select a recorded version'}`));
        button.append(label, node('span', 'View map'));
        button.addEventListener('click', () => {
          if (fieldEditing) return;
          byId('global-plot-select').value = record.field_id;
          selectField(record.field_id);
          showView('myland');
        });
        byId('dashboard-plots').append(button);
      });
      if (!fieldId && fields.length) {
        select.value = fields[0].field_id;
        selectField(select.value);
      }
    }
  });
  async function loadFields() {
    return fieldList.load(fieldsCursor ?? 'first', signal =>
      api.get('/fields', { signal, schema: 'FieldsResponse', params: { cursor: fieldsCursor } }));
  }
  async function readField(id, params, signal) {
    const response = await api.request(`/fields/${encode(id)}`, { signal, params, schema: 'FieldResponse' });
    return { ...response.body, etag: response.etag };
  }
  async function refreshFields(preferred) {
    fields = [];
    fieldsCursor = null;
    fieldId = null;
    fieldList.clear();
    field.clear();
    observations.clear();
    evidence.clear();
    await loadFields();
    if (preferred) {
      await selectField(preferred);
      if (field.state.status === 'ready') {
        const record = field.state.data.data;
        if (!fields.some(item => item.field_id === preferred)) {
          fields.push(record);
          byId('global-plot-select').add(new Option(record.name ?? preferred, preferred));
        }
        byId('global-plot-select').value = preferred;
      }
    }
  }
  const workspace = createResource(state => {
    byId('capabilities').replaceChildren();
    byId('connection-status').parentElement.dataset.state = state.status;
    if (state.status === 'loading') byId('connection-status').textContent = 'Connecting to backend...';
    else if (state.status === 'error') byId('connection-status').textContent = message(state.error);
    else if (state.status === 'ready') {
      const privateAccount = state.data.data.access_mode === 'private_account';
      byId('connection-status').textContent = privateAccount
        ? `Connected - private workspace for ${currentSession.user.login}. Source evidence remains read-only.`
        : 'Connected - account-free shared workspace. Source evidence remains read-only.';
      byId('workspace-access-label').textContent = privateAccount ? 'Private workspace' : 'Shared workspace';
      byId('workspace-notice').textContent = privateAccount
        ? 'Your profile and plots belong to your signed-in account. No shared records are copied into it.'
        : 'Everyone permitted to reach this shared workspace can access its profile and plots.';
      state.data.data.capabilities.forEach(capability => byId('capabilities').append(
        node('li', `${capability.capability_id}: ${capability.state}${capability.reason ? ` - ${capability.reason}` : ''}`)));
    }
  });
  async function connect() {
    const generation = ++bootGeneration;
    profile.setAvailable(false);
    landActions.setCapabilities([]);
    fieldList.clear();
    field.clear();
    observations.clear();
    evidence.clear();
    fields = [];
    fieldsCursor = null;
    fieldId = null;
    canReadObservations = false;
    byId('global-plot-select').replaceChildren(new Option('No field loaded', ''));
    byId('global-plot-select').disabled = true;
    byId('fields-status').textContent = 'Not loaded';
    byId('dash-metric-plots').textContent = '--';
    byId('dash-plots-hint').textContent = 'Waiting for backend';
    byId('dash-metric-source').textContent = 'Not loaded';
    byId('dashboard-plots').replaceChildren();
    await workspace.load('workspace', signal => api.get('/workspace', { signal, schema: 'WorkspaceResponse' }));
    if (generation !== bootGeneration || workspace.state.status !== 'ready') return;
    const capabilities = workspace.state.data.data.capabilities;
    profile.setAvailable(capabilities.some(item => item.capability_id === 'profile' && item.state === 'ready'));
    landActions.setCapabilities(capabilities, workspace.state.data.data.project_ids,
      workspace.state.data.data.access_mode === 'private_account');
    canReadObservations = capabilities.some(item => item.capability_id === 'observations' && item.state === 'ready');
    byId('dash-metric-source').textContent = canReadObservations ? 'Connected' : 'Unavailable';
    if (capabilities.some(item => item.capability_id === 'fields' && item.state === 'ready')) await loadFields();
    else byId('fields-status').textContent = 'Field access is blocked. Configure the backend project scope and prepared database.';
  }
  access = createAccountAccess(api, {
    onReady(session) {
      currentSession = session;
      profile.setIdentity(session.user);
      byId('header-farmer-name').textContent = profileName || session.user?.login || 'Workspace profile';
      return connect();
    },
    onState(text, state) {
      byId('connection-status').textContent = text;
      byId('connection-status').parentElement.dataset.state = state;
    },
    hasDraft: () => profile.hasDraft() || landActions.hasDraft(),
  });
  byId('retry-connection').addEventListener('click', () => access.check());
  byId('global-plot-select').addEventListener('change', event => selectField(event.target.value));
  byId('boundary-select').addEventListener('change', event => {
    const params = { boundary_id: event.target.value };
    field.load(`${fieldId}/${event.target.value}`, signal =>
      readField(fieldId, params, signal));
  });
  byId('more-fields').addEventListener('click', loadFields);
  byId('observation-filters').addEventListener('submit', event => {
    event.preventDefault();
    filters = { variable_id: byId('variable-filter').value.trim(),
      validation_status: byId('validation-filter').value,
      start_date: byId('start-date').value, end_date: byId('end-date').value };
    observationCursors = [null];
    pageIndex = 0;
    loadObservations();
  });
  byId('previous-observations').addEventListener('click', () => { pageIndex--; loadObservations(); });
  byId('next-observations').addEventListener('click', () => {
    observationCursors[++pageIndex] = nextObservationCursor;
    loadObservations();
  });
  byId('next-evidence').addEventListener('click', () => inspect(selectedObservationId, evidenceCursor));
  access.check();
}
