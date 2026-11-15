import { submissionKey, waitForJob } from '../api/jobs.js';
import { boundaryKml, KML_MEDIA_TYPE } from '../api/kml.js';

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
  const previewOriginal = button('Download preview original', 'download-import-original');
  previewOriginal.hidden = true;
  const closePreview = button('Close preview / job', 'close-preview');
  closePreview.hidden = true;

  const exportControls = node('div');
  exportControls.className = 'api-filters';
  const format = control('Download format', 'select', 'export-format', exportControls);
  ['geojson', 'kml', 'kmz'].forEach(value => format.append(new Option(value.toUpperCase(), value)));
  const exportButton = button('Export selected boundary', 'export-boundary');
  const original = button('Download saved original', 'download-boundary-original');
  const download = button('Download completed export', 'download-export');
  download.hidden = true;
  exportControls.append(original, exportButton, download);
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
    node('p', 'Original files are saved first. Review the preview and confirm before creating fields. AI analysis is unavailable.'),
    uploadForm, previewPanel, previewOriginal, confirm);
  const exportSection = section('Download a boundary', 'export-tools',
    node('p', 'The original is the exact source file for the selected saved version. Exports generate new geometry files.'),
    exportControls);
  const jobSection = section('Resume a saved job', 'job-tools', resumeControls);
  container.append(node('h2', 'Plot tools'), status, actions, draftForm, importSection, exportSection,
    jobStatus, closePreview, jobSection);

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
  let activeJob = null;
  let currentPreview = null;
  let downloadId = null;
  let uploadSubmission = null;
  let confirmSubmission = null;
  let exportSubmission = null;
  let resumeStarted = false;
  let downloading = false;

  function render() {
    const writable = capabilities.has('field_writes');
    const importing = capabilities.has('imports');
    const workflow = !!activeJob || !!currentPreview || !!uploadSubmission || !!confirmSubmission || !!exportSubmission;
    const occupied = writing || jobBusy || !!draft || workflow;
    const draftReady = draft?.submittedJob ? capabilities.has('jobs') : draft?.id ? writable : importing;
    create.disabled = !importing || occupied;
    edit.disabled = !writable || !selected || !selectedEtag || occupied;
    archive.disabled = edit.disabled;
    draftControls.disabled = !draftReady || writing || jobBusy || !!draft?.frozen;
    project.disabled = !!draft?.id;
    save.disabled = !draftReady || writing || jobBusy || drawing || !!draft?.blocked;
    save.textContent = draft?.submittedJob ? 'Resume KML preview' : draft?.id ? 'Save field'
      : draft?.frozen ? 'Retry same KML submission' : 'Save KML for preview';
    cancel.disabled = writing;
    finish.disabled = !drawing || writing;
    upload.disabled = !importing || writing || jobBusy || !!draft || !!activeJob || !!currentPreview
      || !!confirmSubmission || !!exportSubmission;
    uploadControls.disabled = upload.disabled || !!uploadSubmission;
    upload.textContent = uploadSubmission ? 'Retry same preview submission' : 'Upload for preview';
    confirm.disabled = !(confirmSubmission?.job ? capabilities.has('jobs') : importing)
      || writing || jobBusy || !!draft || !currentPreview || !!uploadSubmission || !!exportSubmission;
    confirm.textContent = confirmSubmission?.job ? 'Resume confirmation'
      : confirmSubmission ? 'Retry same confirmation' : 'Confirm selected valid boundaries';
    previewPanel.querySelectorAll('input').forEach(input => {
      input.disabled = writing || jobBusy || !!confirmSubmission || !!currentPreview?.confirmed_job_id;
    });
    exportButton.disabled = !capabilities.has('exports') || writing || jobBusy || !!draft || !!activeJob
      || !!currentPreview || !!uploadSubmission || !!confirmSubmission || !selected?.selected_boundary_id;
    exportButton.textContent = exportSubmission ? 'Retry same export submission' : 'Export selected boundary';
    format.disabled = exportButton.disabled || !!exportSubmission;
    download.disabled = downloading || !downloadId;
    original.disabled = !capabilities.has('boundary_originals') || downloading || occupied || !selected?.selected_boundary_id;
    previewOriginal.hidden = !currentPreview && !activeJob?.kind.startsWith('import_');
    previewOriginal.disabled = !capabilities.has('boundary_originals') || downloading;
    closePreview.hidden = !workflow && !downloadId;
    closePreview.disabled = writing;
    const uncertain = !!uploadSubmission || !!exportSubmission || (!!confirmSubmission && !confirmSubmission.job);
    resume.disabled = !capabilities.has('jobs') || writing || jobBusy || uncertain || (!!draft && !draft.submittedJob);
    resumeId.disabled = writing || jobBusy || uncertain || !!draft || !!currentPreview || !!activeJob;
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
    lockSelection(!!draft || writing || jobBusy || workflow);
  }
  function clearWorkflow() {
    jobController?.abort();
    jobGeneration++;
    jobBusy = false;
    activeJob = null;
    currentPreview = null;
    uploadSubmission = null;
    confirmSubmission = null;
    exportSubmission = null;
    downloadId = null;
    download.hidden = true;
    confirm.hidden = true;
    previewPanel.replaceChildren();
    resumeId.value = '';
    const url = new URL(window.location.href);
    url.searchParams.delete('job');
    window.history.replaceState(null, '', url);
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
      : 'Draw or supply a real boundary. Save its KML, review the backend preview, then confirm your plot. AI is unavailable.';
    render();
  }
  create.addEventListener('click', () => openDraft(null, null));
  edit.addEventListener('click', () => openDraft(selected, selectedEtag));
  cancel.addEventListener('click', async () => {
    const target = draft?.id;
    const jobId = draft?.submittedJob?.job_id;
    if (!target && (draft?.pending || draft?.submittedJob || currentPreview)) clearWorkflow();
    closeDraft();
    status.textContent = 'Local draft discarded. Stored files and server jobs are not deleted or cancelled.'
      + (jobId ? ` Resume ${jobId} to check its outcome.` : '');
    await refresh(target);
  });
  closePreview.addEventListener('click', () => {
    if (closePreview.disabled) return;
    const identifier = resumeId.value;
    const submittedDraft = !!draft?.submittedJob;
    clearWorkflow();
    if (submittedDraft) closeDraft();
    else if (!draft) map.clearPreview();
    jobStatus.textContent = 'Preview/job closed locally. Stored originals and server jobs are not deleted or cancelled.'
      + (identifier ? ` Resume ${identifier} to check its outcome.` : '');
    status.textContent = draft ? 'Your editable geometry draft is retained.' : 'No active preview. Saved fields are unchanged.';
    render();
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
    if (draft.submittedJob) { await monitor(draft.submittedJob); return; }
    let body;
    try {
      body = draft.pending;
      if (!body) {
        const value = geometry.value.trim() ? JSON.parse(geometry.value) : null;
        const label = name.value.trim() ? name.value : null;
        if (!draft.id) {
          if (!value) throw new Error('Supply a boundary before creating a field.');
          body = { project: project.value, file: new Blob([
            boundaryKml(value, { name: label, id: `drawn-${draft.key}` }),
          ], { type: KML_MEDIA_TYPE }) };
        } else {
          body = {};
          if (label !== draft.original.name) body.name = label;
          if (value && JSON.stringify(value) !== JSON.stringify(draft.original.geometry)) body.geometry = value;
          if (!Object.keys(body).length) { status.textContent = 'No field changes to save.'; return; }
        }
      }
    } catch (error) { status.textContent = `Invalid geometry draft: ${error.message}`; return; }
    writing = true;
    if (!draft.id) {
      currentPreview = null;
      previewPanel.replaceChildren();
      confirm.hidden = true;
    }
    render();
    let job;
    try {
      if (draft.id) {
        const response = await api.request(`/fields/${encodeURIComponent(draft.id)}`, {
          method: 'PATCH', body, schema: 'FieldMutationResponse', headers: { 'If-Match': draft.etag },
        });
        const id = response.body.data.field_id;
        closeDraft();
        status.textContent = `Saved field ${id}. User-supplied geometry is not scientific verification.`;
        await refresh(id);
      } else {
        const response = await api.request('/imports', { method: 'POST', rawBody: body.file,
          params: { filename: 'drawn-plot.kml', project_id: body.project, source_namespace: 'drawn' },
          headers: { 'Content-Type': KML_MEDIA_TYPE, 'Idempotency-Key': draft.key }, schema: 'JobResponse' });
        job = draft.submittedJob = response.body.data;
        draft.pending = body;
        draft.frozen = true;
        status.textContent = 'KML saved on the backend. Waiting for its preview; no field has been confirmed and AI is unavailable.';
      }
    } catch (error) {
      if (!draft?.id && error.outcomeUncertain) {
        draft.pending = body;
        draft.frozen = true;
      } else if (draft?.id && (error.outcomeUncertain || error.status === 412)) draft.blocked = true;
      else if (draft && !draft.id) {
        draft.pending = null;
        draft.frozen = false;
        draft.key = newKey();
      }
      status.textContent = `${describe(error)} Draft retained. ${draft?.frozen
        ? 'Retry the same submission to resolve its outcome without creating a duplicate.'
        : draft?.blocked ? 'Discard and reload before another write.' : ''}`;
    } finally { writing = false; render(); }
    if (job) await monitor(job);
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
        status.textContent = 'Orange dashed geometry is the source preview. Check confirmation before treating it as a saved field.';
      });
      row.append(label, inspect);
      previewPanel.append(row);
    });
    info.rejected.forEach(item => previewPanel.append(node('p', `Rejected ${item.locator}: ${item.reason}`)));
    confirm.hidden = !info.candidates.length || !!info.confirmed_job_id;
    if (!draft && info.candidates.length === 1) map.previewGeometry(info.candidates[0].geometry);
    if (!draft) status.textContent = info.confirmed_job_id
      ? 'Original file saved. Check the existing confirmation job for field status.'
      : `${info.filename.toLowerCase().endsWith('.kml') ? 'KML' : 'Original file'} saved. `
        + 'Review the orange preview and explicitly confirm to save a field. AI analysis is unavailable.';
  }
  async function monitor(job) {
    const generation = ++jobGeneration;
    jobController?.abort();
    jobController = new AbortController();
    activeJob = job;
    jobBusy = true;
    if (job.kind.startsWith('import_')) importSection.open = true;
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
      if (['failed', 'succeeded'].includes(finished.status)) {
        if (finished.kind === 'import_preview') {
          const info = await api.get(`/imports/${encodeURIComponent(finished.resource_id)}`, { schema: 'ImportResponse' });
          if (generation !== jobGeneration) return;
          if (draft?.submittedJob?.job_id === finished.job_id) {
            if (finished.status === 'succeeded' && info.data.candidates.length) closeDraft();
            else {
              draft.submittedJob = null;
              draft.pending = null;
              draft.frozen = false;
              draft.key = newKey();
              status.textContent = 'KML retained, but no valid boundary was produced. Correct the draft and save a new preview.';
            }
          }
          showPreview(info.data);
        } else if (finished.kind === 'import_confirm' && finished.status === 'succeeded') {
          const kml = currentPreview?.filename.toLowerCase().endsWith('.kml');
          confirm.hidden = true;
          currentPreview = null;
          confirmSubmission = null;
          const saved = `${kml ? 'KML' : 'Boundary and original file'} saved; AI analysis unavailable.`;
          previewPanel.replaceChildren(node('p', `Selected boundaries were committed atomically. ${saved}`));
          status.textContent = saved;
          map.clearPreview();
          await refresh(finished.result.fields[0]?.field_id);
        } else if (finished.kind === 'export' && finished.status === 'succeeded') {
          exportSection.open = true;
          downloadId = finished.resource_id;
          download.hidden = false;
        }
        if (generation !== jobGeneration) return;
        activeJob = null;
        if (finished.status === 'failed') {
          if (finished.kind === 'import_confirm') { confirm.hidden = true; confirmSubmission = null; }
          jobStatus.textContent += ' No automatic resubmission will occur. Correct your draft or close this preview/job before starting again.';
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
    writing = true;
    currentPreview = null;
    previewPanel.replaceChildren();
    confirm.hidden = true;
    render();
    let job;
    try {
      const response = await api.request('/imports', { method: 'POST', rawBody: uploadSubmission.file,
        params: { filename: uploadSubmission.file.name, project_id: uploadSubmission.project,
          source_namespace: uploadSubmission.namespace },
        headers: { 'Content-Type': 'application/octet-stream', 'Idempotency-Key': uploadSubmission.key },
        schema: 'JobResponse' });
      uploadSubmission = null;
      job = response.body.data;
    } catch (error) {
      if (!error.outcomeUncertain) uploadSubmission = null;
      jobStatus.textContent = `${describe(error)}${uploadSubmission ? ' Retry the same preview submission to recover its job.' : ''}`;
    } finally { writing = false; render(); }
    if (job) await monitor(job);
  });
  confirm.addEventListener('click', async () => {
    if (confirm.disabled || !currentPreview) return;
    if (confirmSubmission?.job) { await monitor(confirmSubmission.job); return; }
    const ids = [...previewPanel.querySelectorAll('input:checked')].map(input => input.value);
    if (!ids.length || ids.length > 50) { jobStatus.textContent = 'Select between 1 and 50 valid candidates.'; return; }
    confirmSubmission ??= { key: newKey(), body: { preview_hash: currentPreview.preview_hash, candidate_ids: ids } };
    writing = true;
    render();
    let job;
    try {
      const response = await api.request(`/imports/${encodeURIComponent(currentPreview.import_id)}/confirm`, {
        method: 'POST', body: confirmSubmission.body, headers: { 'Idempotency-Key': confirmSubmission.key },
        schema: 'JobResponse',
      });
      job = confirmSubmission.job = response.body.data;
      currentPreview.confirmed_job_id = job.job_id;
    } catch (error) {
      if (!error.outcomeUncertain) confirmSubmission = null;
      jobStatus.textContent = `${describe(error)} ${confirmSubmission
        ? 'Selection retained; retry only this same confirmation to recover its job.'
        : 'No confirmation was accepted. Review the selection or close this preview before starting again.'}`;
    } finally { writing = false; render(); }
    if (job) await monitor(job);
  });
  exportButton.addEventListener('click', async () => {
    if (exportButton.disabled) return;
    exportSubmission ??= { key: newKey(), body: { format: format.value, fields: [{
      field_id: selected.field_id, boundary_id: selected.selected_boundary_id }] } };
    writing = true;
    downloadId = null;
    download.hidden = true;
    render();
    let job;
    try {
      const response = await api.request('/exports', { method: 'POST', body: exportSubmission.body,
        headers: { 'Idempotency-Key': exportSubmission.key }, schema: 'JobResponse' });
      exportSubmission = null;
      job = response.body.data;
    } catch (error) {
      if (!error.outcomeUncertain) exportSubmission = null;
      jobStatus.textContent = `${describe(error)}${exportSubmission ? ' Retry to recover the same export job.' : ''}`;
    } finally { writing = false; render(); }
    if (job) await monitor(job);
  });
  async function downloadFile(path) {
    if (downloading) return;
    downloading = true;
    render();
    try {
      const response = await api.request(path, { responseType: 'blob' });
      const url = URL.createObjectURL(response.body);
      const link = node('a');
      link.href = url;
      link.download = response.disposition.match(/filename="([^"]+)"/)[1];
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { jobStatus.textContent = describe(error); }
    finally { downloading = false; render(); }
  }
  download.addEventListener('click', () => {
    if (!download.disabled) downloadFile(`/exports/${encodeURIComponent(downloadId)}/download`);
  });
  original.addEventListener('click', () => {
    if (!original.disabled) downloadFile(`/fields/${encodeURIComponent(selected.field_id)}`
      + `/boundaries/${encodeURIComponent(selected.selected_boundary_id)}/original`);
  });
  previewOriginal.addEventListener('click', () => {
    const id = currentPreview?.import_id ?? activeJob?.resource_id;
    if (id && !previewOriginal.disabled) downloadFile(`/imports/${encodeURIComponent(id)}/download`);
  });
  async function resumeJob() {
    if (resume.disabled) return;
    const identifier = resumeId.value.trim();
    if (!/^job_[a-f0-9]{32}$/.test(identifier)) { jobStatus.textContent = 'Enter a valid backend job ID.'; return; }
    const expected = draft?.submittedJob?.job_id ?? activeJob?.job_id
      ?? currentPreview?.confirmed_job_id ?? currentPreview?.preview_job_id;
    if (expected && identifier !== expected) {
      jobStatus.textContent = 'Close the current preview/job before selecting a different job.';
      return;
    }
    writing = true;
    render();
    let job;
    try {
      const response = await api.get(`/jobs/${identifier}`, { schema: 'JobResponse' });
      job = response.data;
    } catch (error) { jobStatus.textContent = describe(error); }
    finally { writing = false; render(); }
    if (job) await monitor(job);
  }
  resume.addEventListener('click', resumeJob);
  render();
  return {
    hasDraft: () => !!draft || writing || jobBusy || !!activeJob || !!uploadSubmission || !!confirmSubmission
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
      if (!draft && !writing && !currentPreview && !activeJob) status.textContent = capabilities.has('field_writes')
        ? capabilities.has('imports') ? 'Draw or import a boundary, review its saved original and confirm your plot. AI is unavailable.'
          : 'Existing fields may be edited. New KML previews require an available import worker.'
        : 'Field editing is unavailable until the backend storage is ready.';
      if (!projectIds.length) { render(); return; }
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
