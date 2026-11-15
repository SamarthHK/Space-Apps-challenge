import { ApiError } from './client.js';

export function submissionKey(random = crypto) {
  return [...random.getRandomValues(new Uint8Array(16))].map(value => value.toString(16).padStart(2, '0')).join('');
}

function pause(milliseconds, signal) {
  return new Promise((resolve, reject) => {
    const abort = () => { clearTimeout(timer); reject(new ApiError('aborted', 'Job monitoring cancelled.')); };
    const timer = setTimeout(() => { signal?.removeEventListener('abort', abort); resolve(); }, milliseconds);
    if (signal?.aborted) abort();
    else signal?.addEventListener('abort', abort, { once: true });
  });
}

export async function waitForJob(api, job, { signal, onUpdate = () => {}, intervalMs = 750, maxWaitMs = 120000 } = {}) {
  const started = Date.now();
  while (true) {
    const response = await api.get(`/jobs/${encodeURIComponent(job.job_id)}`, { signal, schema: 'JobResponse' });
    job = response.data;
    onUpdate(job);
    if (['succeeded', 'failed'].includes(job.status) || Date.now() - started >= maxWaitMs) return job;
    await pause(intervalMs, signal);
  }
}
