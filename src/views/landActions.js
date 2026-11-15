import { submissionKey, waitForJob } from '../api/jobs.js';

const node = (tag, text, id) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (id) element.id = id;
  return element;
};
const button = (text, id) => {
  const element = node('button', text, id);
  element.type = 'button';
  element.className = 'btn-secondary';
  return element;
};
const control = (title, tag, id, parent) => {
  const label = node('label', title);
  const input = node(tag, undefined, id);
  input.className = tag === 'select' ? 'form-select' : 'form-input';
  label.append(input);
  parent.append(label);
  return input;
};
const describe = error => `${error.message}${error.requestId ? ` (Request ${error.requestId})` : ''}`;
const newKey = submissionKey;

export function createLandActions(container, api, map, { refresh, lockSelection, revealTools = () => {} }) {
  const status = node('p', 'Connect to the backend before editing fields.', 'field-write-status');
  status.setAttribute('role', 'status');
  const create = button('New field', 'new-field');
  const edit = button('Edit selected field', 'edit-field');
  const archive = button('Archive selected field', 'archive-field');
  const draftForm = node('form', undefined, 'field-editor');
  const draftControls = node('fieldset');
  draftControls.className = 'api-filters';
  const name = control('Field name (optional)', 'input', 'field-name', draftControls);
  name.maxLength = 200;
  const project = control('Project', 'select', 'field-project', draftControls);
  const geometry = control('GeoJSON geometry (longitude, latitude)', 'textarea', 'field-geometry', draftControls);
  geometry.rows = 4;
  const draw = button('Draw replacement polygon', 'draw-field');
  const finish = button('Finish drawing', 'finish-drawing');
  const centerControls = node('div');
  centerControls.className = 'api-filters';
  const longitude = control('Map center longitude', 'input', 'map-longitude', centerControls);
  const latitude = control('Map center latitude', 'input', 'map-latitude', centerControls);
  for (const input of [longitude, latitude]) { input.type = 'number'; input.step = 'any'; }
  const center = button('Move map (not a boundary)', 'center-map');
  centerControls.append(center);
  draftControls.append(draw, finish, centerControls,
    node('p', 'Click the map to add vertices; drag handles to move them, then finish. Drawing replaces all parts and holes. '
      + 'Use GeoJSON to edit complex geometry without dropping parts. Nothing is saved until you submit.'));
  const save = button('Save field', 'save-field');
  save.type = 'submit';
  save.className = 'btn-primary';
  const cancel = button('Discard draft and reload', 'cancel-field');
  draftForm.append(draftControls, save, cancel);
  draftForm.hidden = true;

  const uploadForm = node('form', undefined, 'boundary-upload-form');
  const uploadControls = node('fieldset');
  uploadControls.className = 'api-filters';
  const file = control('Boundary file (KML, KMZ, GeoJSON; at most 16 MiB)', 'input', 'boundary-file', uploadControls);
  file.type = 'file';
  file.accept = '.kml,.kmz,.geojson';
  file.required = true;
  const importProject = control('Import project', 'select', 'import-project', uploadControls);
  const namespace = control('Stable source namespace', 'input', 'import-namespace', uploadControls);
  namespace.value = 'uploads';
  namespace.maxLength = 80;
  namespace.required = true;
  const upload = button('Upload for preview', 'preview-import');
  upload.type = 'submit';
  uploadForm.append(uploadControls, upload);
  const previewPanel = node('div', undefined, 'boundary-preview');
  const confirm = button('Confirm selected valid boundaries', 'confirm-import');
  confirm.hidden = true;

  const exportControls = node('div');
  exportControls.className = 'api-filters';
  const format = control('Download format', 'select', 'export-format', exportControls);
  ['geojson', 'kml', 'kmz'].forEach(value => format.append(new Option(value.toUpperCase(), value)));
  const exportButton = button('Export selected boundary', 'export-boundary');
  const download = button('Download completed export', 'download-export');
  download.hidden = true;
  exportControls.append(exportButton, download);
  const jobStatus = node('p', 'No import or export job selected.', 'job-status');
  jobStatus.setAttribute('role', 'status');
  const resumeControls = node('div');
  resumeControls.className = 'api-filters';
  const resumeId = control('Job ID (saved in the page URL for reload)', 'input', 'resume-job-id', resumeControls);
  const resume = button('Resume job monitoring', 'resume-job');
  resumeControls.append(resume);
  const actions = node('div');
  actions.className = 'field-action-row';
  actions.append(create, edit, archive);
  function section(title, id, ...children) {
    const element = node('details', undefined, id);
    element.className = 'tool-section';
    element.append(node('summary', title), ...children);
    return element;
  }
  const importSection = section('Import a boundary', 'import-tools',
    node('p', 'Upload original geometry, review its unsaved preview and confirm before creating fields.'),
    uploadForm, previewPanel, confirm);
  const exportSection = section('Download a boundary', 'export-tools', exportControls);
  const jobSection = section('Resume a saved job', 'job-tools', resumeControls);
  container.append(node('h2', 'Plot tools'), status, actions, draftForm, importSection, exportSection, jobStatus, jobSection);

  let capabilities = new Set();
  let projects = [];
  let selected = null;
  let selectedEtag = null;
  let draft = null;
  let writing = false;
  let drawing = false;
  let pointCount = 0;
  let jobBusy = false;
  let jobGeneration = 0;
  let jobController;
  let currentPreview = null;
  let downloadId = null;
  let uploadSubmission = null;
  let confirmSubmission = null;
  let exportSubmission = null;
  let resumeStarted = false;

  function render() {
    const writable = capabilities.has('field_writes');
    create.disabled = !writable || writing || !!draft;
    edit.disabled = !writable || !selected || !selectedEtag || writing || !!draft;
    archive.disabled = edit.disabled;
    draftControls.disabled = !writable || writing || !!draft?.frozen;
    project.disabled = !!draft?.id;
    save.disabled = !writable || writing || drawing || !!draft?.blocked;
    save.textContent = draft?.frozen ? 'Retry same field submission' : 'Save field';
    cancel.disabled = writing;
    finish.disabled = !drawing || writing;
    uploadControls.disabled = !capabilities.has('imports') || jobBusy || !!uploadSubmission;
    upload.disabled = !capabilities.has('imports') || jobBusy;
    upload.textContent = uploadSubmission ? 'Retry same preview submission' : 'Upload for preview';
    confirm.disabled = !capabilities.has('imports') || jobBusy || !currentPreview;
    exportButton.disabled = !capabilities.has('exports') || jobBusy || !selected?.selected_boundary_id;
    exportButton.textContent = exportSubmission ? 'Retry same export submission' : 'Export selected boundary';
    format.disabled = jobBusy || !!exportSubmission;
    download.disabled = jobBusy || !downloadId;
    resume.disabled = !capabilities.has('jobs') || jobBusy;
    for (const id of ['btn-start-drawing', 'btn-dash-add-plot', 'act-draw-plot']) {
      document.getElementById(id).disabled = create.disabled;
    }
    for (const id of ['btn-upload-boundary', 'btn-dash-import']) {
      document.getElementById(id).disabled = upload.disabled;
    }
    for (const id of ['btn-export-kml', 'btn-export-current-geojson']) {
      document.getElementById(id).disabled = exportButton.disabled;
    }
    document.getElementById('draw-helper-banner').hidden = !drawing;
    document.getElementById('draw-points-count').textContent = `${pointCount} points`;
    document.getElementById('btn-finish-drawing').disabled = finish.disabled || pointCount < 3;
    document.getElementById('btn-undo-drawing').disabled = !drawing || !pointCount || writing;
    document.getElementById('btn-cancel-drawing').disabled = writing;
    lockSelection(!!draft || writing);
  }
  function closeDraft() {
    draft = null;
    drawing = false;
    draftForm.hidden = true;
    map.clearPreview();
    render();
  }
  function openDraft(record, etag) {
    revealTools();
    draft = { id: record?.field_id ?? null, etag, original: record, key: newKey() };
    name.value = record?.name ?? '';
    project.value = record?.project_id ?? projects[0] ?? '';
    geometry.value = record?.geometry ? JSON.stringify(record.geometry, null, 2) : '';
    if (record?.representative_point) {
      [longitude.value, latitude.value] = record.representative_point.coordinates;
    }
    draftForm.hidden = false;
    status.textContent = record ? `Editing ${record.field_id}; existing boundary history will be retained.`
      : 'New field draft. Draw or supply a real boundary; no geometry is generated for you.';
    render();
  }
  create.addEventListener('click', () => openDraft(null, null));
  edit.addEventListener('click', () => openDraft(selected, selectedEtag));
  cancel.addEventListener('click', async () => {
    const target = draft?.id;
    closeDraft();
    status.textContent = 'Local draft discarded. This does not undo any completed server write.';
    await refresh(target);
  });
  draw.addEventListener('click', () => {
    drawing = true;
    pointCount = 0;
    geometry.value = '';
    map.startDrawing((value, count) => {
      geometry.value = value ? JSON.stringify(value, null, 2) : '';
      pointCount = count;
      render();
    });
    status.textContent = 'Drawing a replacement polygon. Click at least three map points, then finish.';
    render();
  });
  finish.addEventListener('click', () => {
    if (!map.finishDrawing()) { status.textContent = 'Add at least three vertices before finishing.'; return; }
    drawing = false;
    status.textContent = 'Geometry draft ready for review. It has not been saved.';
    render();
    name.focus();
  });
  document.getElementById('btn-finish-drawing').addEventListener('click', () => finish.click());
  document.getElementById('btn-cancel-drawing').addEventListener('click', () => cancel.click());
  document.getElementById('btn-undo-drawing').addEventListener('click', () => map.undoDrawing());
  center.addEventListener('click', () => {
    const x = Number(longitude.value), y = Number(latitude.value);
    if (!longitude.value || !latitude.value || !Number.isFinite(x) || !Number.isFinite(y) ||
        x < -180 || x > 180 || y < -80 || y > 84) {
      status.textContent = 'Enter a longitude (-180 to 180) and supported latitude (-80 to 84).';
      return;
    }
    map.center(x, y);
  });
  draftForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!draft || save.disabled) return;
    let body;
    try {
      body = draft.pending;
      if (!body) {
        const value = geometry.value.trim() ? JSON.parse(geometry.value) : null;
        const label = name.value.trim() ? name.value : null;
        if (!draft.id) {
          if (!value) throw new Error('Supply a boundary before creating a field.');
          body = { project_id: project.value, name: label, geometry: value };
        } else {
          body = {};
          if (label !== draft.original.name) body.name = label;
          if (value && JSON.stringify(value) !== JSON.stringify(draft.original.geometry)) body.geometry = value;
          if (!Object.keys(body).length) { status.textContent = 'No field changes to save.'; return; }
        }
      }
    } catch (error) { status.textContent = `Invalid geometry draft: ${error.message}`; return; }
    writing = true;
    render();
    try {
      const response = await api.request(draft.id ? `/fields/${encodeURIComponent(draft.id)}` : '/fields', {
        method: draft.id ? 'PATCH' : 'POST', body, schema: 'FieldMutationResponse',
        headers: draft.id ? { 'If-Match': draft.etag } : { 'Idempotency-Key': draft.key },
      });
      const id = response.body.data.field_id;
      closeDraft();
      status.textContent = `Saved field ${id}. User-supplied geometry is not scientific verification.`;
      await refresh(id);
    } catch (error) {
      if (!draft?.id && error.outcomeUncertain) {
        draft.pending = body;
        draft.frozen = true;
      } else if (draft?.id && (error.outcomeUncertain || error.status === 412)) draft.blocked = true;
      status.textContent = `${describe(error)} Draft retained. ${draft?.frozen
        ? 'Retry the same submission to resolve its outcome without creating a duplicate.'
        : draft?.blocked ? 'Discard and reload before another write.' : ''}`;
    } finally { writing = false; render(); }
  });
  archive.addEventListener('click', async () => {
    if (!selected || archive.disabled || !window.confirm(
      'Archive this field? It will disappear from normal views; boundary and evidence history is retained.')) return;
    writing = true;
    render();
    try {
      await api.request(`/fields/${encodeURIComponent(selected.field_id)}`, {
        method: 'DELETE', headers: { 'If-Match': selectedEtag }, schema: 'FieldMutationResponse',
      });
      status.textContent = 'Field archived; historical data was not deleted.';
      await refresh();
    } catch (error) { status.textContent = `${describe(error)} Reconnect to check the current field before retrying.`; }
    finally { writing = false; render(); }
  });

  function showPreview(info) {
    importSection.open = true;
    currentPreview = info;
    confirmSubmission = null;
    previewPanel.replaceChildren(node('p',
      `${info.candidates.length} valid candidates; ${info.rejected.length} rejected. `
      + (info.confirmed_job_id ? `Confirmation job: ${info.confirmed_job_id}. Check its outcome.`
        : 'Nothing has been saved as a field yet.')));
    if (info.confirmed_job_id) {
      const check = button('Check existing confirmation');
      check.addEventListener('click', () => { resumeId.value = info.confirmed_job_id; resumeJob(); });
      previewPanel.append(check);
    }
    info.candidates.forEach(candidate => {
      const row = node('div');
      const label = node('label');
      const checkbox = node('input');
      checkbox.type = 'checkbox';
      checkbox.value = candidate.candidate_id;
      checkbox.checked = info.candidates.length <= 50;
      label.append(checkbox, document.createTextNode(
        ` ${candidate.action}: ${candidate.name ?? candidate.field_id}; ${candidate.area_m2.toFixed(2)} m2; `
        + `${candidate.metric_crs}; ${candidate.locator}`));
      const inspect = button('View preview');
      inspect.addEventListener('click', () => {
        map.previewGeometry(candidate.geometry);
        status.textContent = 'Orange dashed geometry is an unsaved import preview, not a stored field.';
      });
      row.append(label, inspect);
      previewPanel.append(row);
    });
    info.rejected.forEach(item => previewPanel.append(node('p', `Rejected ${item.locator}: ${item.reason}`)));
    confirm.hidden = !info.candidates.length || !!info.confirmed_job_id;
  }
  async function monitor(job) {
    const generation = ++jobGeneration;
    jobController?.abort();
    jobController = new AbortController();
    jobBusy = true;
    resumeId.value = job.job_id;
    const url = new URL(window.location.href);
    url.searchParams.set('job', job.job_id);
    window.history.replaceState(null, '', url);
    render();
    try {
      const finished = await waitForJob(api, job, {
        signal: jobController.signal,
        onUpdate(value) {
          if (generation === jobGeneration) jobStatus.textContent =
            `${value.kind}: ${value.status}; attempt ${value.attempts}. Job ${value.job_id}`
            + (value.error ? ` - ${value.error.message}` : '');
        },
      });
      if (generation !== jobGeneration) return;
      if (finished.status === 'failed') {
        jobStatus.textContent += ' No automatic resubmission will occur. Resolve the error and start a fresh preview/export.';
      } else if (finished.status === 'succeeded') {
        if (finished.kind === 'import_preview') {
          const info = await api.get(`/imports/${encodeURIComponent(finished.resource_id)}`, { schema: 'ImportResponse' });
          if (generation === jobGeneration) showPreview(info.data);
        } else if (finished.kind === 'import_confirm') {
          confirm.hidden = true;
          currentPreview = null;
          previewPanel.replaceChildren(node('p', 'Selected boundaries were committed atomically.'));
          map.clearPreview();
          await refresh(finished.result.fields[0]?.field_id);
        } else {
          exportSection.open = true;
          downloadId = finished.resource_id;
          download.hidden = false;
        }
      } else jobStatus.textContent += ' Monitoring paused; resume this durable job to check again.';
    } catch (error) {
      if (generation === jobGeneration) jobStatus.textContent =
        `${describe(error)} The server job was not cancelled. Resume ${job.job_id} to check its outcome.`;
    } finally {
      if (generation === jobGeneration) { jobBusy = false; render(); }
    }
  }
  uploadForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (upload.disabled) return;
    const input = file.files[0];
    if (!uploadSubmission && (!input || input.size === 0 || input.size > 16 * 1024 * 1024)) {
      jobStatus.textContent = 'Choose a nonempty KML, KMZ or GeoJSON file up to 16 MiB.';
      return;
    }
    uploadSubmission ??= { file: input, project: importProject.value, namespace: namespace.value, key: newKey() };
    jobBusy = true;
    currentPreview = null;
    previewPanel.replaceChildren();
    confirm.hidden = true;
    render();
    try {
      const response = await api.request('/imports', { method: 'POST', rawBody: uploadSubmission.file,
        params: { filename: uploadSubmission.file.name, project_id: uploadSubmission.project,
          source_namespace: uploadSubmission.namespace },
        headers: { 'Content-Type': 'application/octet-stream', 'Idempotency-Key': uploadSubmission.key },
        schema: 'JobResponse' });
      uploadSubmission = null;
      await monitor(response.body.data);
    } catch (error) {
      if (!error.outcomeUncertain) uploadSubmission = null;
      jobStatus.textContent = `${describe(error)}${uploadSubmission ? ' Retry the same preview submission to recover its job.' : ''}`;
    } finally { jobBusy = false; render(); }
  });
  confirm.addEventListener('click', async () => {
    if (confirm.disabled || !currentPreview) return;
    const ids = [...previewPanel.querySelectorAll('input:checked')].map(input => input.value);
    if (!ids.length || ids.length > 50) { jobStatus.textContent = 'Select between 1 and 50 valid candidates.'; return; }
    confirmSubmission ??= { key: newKey(), body: { preview_hash: currentPreview.preview_hash, candidate_ids: ids } };
    jobBusy = true;
    previewPanel.querySelectorAll('input').forEach(input => { input.disabled = true; });
    render();
    try {
      const response = await api.request(`/imports/${encodeURIComponent(currentPreview.import_id)}/confirm`, {
        method: 'POST', body: confirmSubmission.body, headers: { 'Idempotency-Key': confirmSubmission.key },
        schema: 'JobResponse',
      });
      await monitor(response.body.data);
      confirmSubmission = null;
    } catch (error) {
      jobStatus.textContent = `${describe(error)} Selection retained; retry only this same confirmation to recover its job.`;
    } finally { jobBusy = false; render(); }
  });
  exportButton.addEventListener('click', async () => {
    if (exportButton.disabled) return;
    exportSubmission ??= { key: newKey(), body: { format: format.value, fields: [{
      field_id: selected.field_id, boundary_id: selected.selected_boundary_id }] } };
    jobBusy = true;
    downloadId = null;
    download.hidden = true;
    render();
    try {
      const response = await api.request('/exports', { method: 'POST', body: exportSubmission.body,
        headers: { 'Idempotency-Key': exportSubmission.key }, schema: 'JobResponse' });
      exportSubmission = null;
      await monitor(response.body.data);
    } catch (error) {
      if (!error.outcomeUncertain) exportSubmission = null;
      jobStatus.textContent = `${describe(error)}${exportSubmission ? ' Retry to recover the same export job.' : ''}`;
    } finally { jobBusy = false; render(); }
  });
  download.addEventListener('click', async () => {
    if (!downloadId || download.disabled) return;
    download.disabled = true;
    try {
      const response = await api.request(`/exports/${encodeURIComponent(downloadId)}/download`, { responseType: 'blob' });
      const url = URL.createObjectURL(response.body);
      const link = node('a');
      link.href = url;
      link.download = response.disposition.match(/filename="([^"]+)"/)[1];
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { jobStatus.textContent = describe(error); }
    finally { render(); }
  });
  async function resumeJob() {
    const identifier = resumeId.value.trim();
    if (!/^job_[a-f0-9]{32}$/.test(identifier)) { jobStatus.textContent = 'Enter a valid backend job ID.'; return; }
    try {
      const response = await api.get(`/jobs/${identifier}`, { schema: 'JobResponse' });
      await monitor(response.data);
    } catch (error) { jobStatus.textContent = describe(error); }
  }
  resume.addEventListener('click', resumeJob);
  render();
  return {
    hasDraft: () => !!draft || writing || jobBusy || !!uploadSubmission || !!confirmSubmission
      || !!exportSubmission || (!!currentPreview && !currentPreview.confirmed_job_id),
    startDrawing() {
      if (create.disabled) return;
      openDraft(null, null);
      draw.click();
    },
    openImport() {
      revealTools();
      importSection.open = true;
      importSection.scrollIntoView({ block: 'nearest' });
    },
    export(value) {
      revealTools();
      exportSection.open = true;
      if (!exportSubmission) { format.value = value; exportButton.click(); }
    },
    setField(record, etag) { selected = record; selectedEtag = etag; render(); },
    setCapabilities(values, projectIds = [], privateAccount = false) {
      capabilities = new Set(values.filter(item => item.state === 'ready').map(item => item.capability_id));
      if (!draft && !writing) status.textContent = capabilities.has('field_writes')
        ? 'Draw or import a boundary to register a plot. Saved changes are retained by the backend.'
        : 'Field editing is unavailable until the backend storage is ready.';
      projects = projectIds;
      for (const select of [project, importProject]) {
        const previous = select.value;
        select.parentElement.hidden = privateAccount;
        select.replaceChildren(...projects.map(value => new Option(privateAccount ? 'My private plots' : value, value)));
        select.value = projects.includes(previous) ? previous : projects[0] ?? '';
      }
      if (currentPreview && !projects.includes(currentPreview.project_id)) {
        currentPreview = null;
        previewPanel.replaceChildren();
        confirm.hidden = true;
      }
      render();
      if (!resumeStarted && capabilities.has('jobs')) {
        resumeStarted = true;
        const identifier = new URL(window.location.href).searchParams.get('job');
        if (identifier) { resumeId.value = identifier; resumeJob(); }
      }
    },
  };
}
