import { test } from 'node:test';
import assert from 'node:assert/strict';
import { submissionKey, waitForJob } from '../src/api/jobs.js';

test('submission keys work without secure-context-only crypto.randomUUID', () => {
  const random = { getRandomValues: bytes => { bytes.fill(171); return bytes; } };
  assert.equal(submissionKey(random), 'ab'.repeat(16));
});

test('job monitoring only reads and stops on terminal states', async () => {
  const states = ['queued', 'running', 'succeeded'];
  const seen = [];
  const api = { get: async path => {
    assert.equal(path, '/jobs/job_identifier');
    return { data: { job_id: 'job_identifier', status: states.shift() } };
  } };
  const result = await waitForJob(api, { job_id: 'job_identifier' }, {
    intervalMs: 0, onUpdate: job => seen.push(job.status),
  });
  assert.equal(result.status, 'succeeded');
  assert.deepEqual(seen, ['queued', 'running', 'succeeded']);
});

test('paused or cancelled monitoring never cancels or resubmits the server job', async () => {
  let reads = 0;
  const api = { get: async () => { reads++; return { data: { job_id: 'job_identifier', status: 'queued' } }; } };
  const result = await waitForJob(api, { job_id: 'job_identifier' }, { maxWaitMs: 0 });
  assert.equal(result.status, 'queued');
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(waitForJob(api, { job_id: 'job_identifier' }, { signal: controller.signal }), { code: 'aborted' });
  assert.equal(reads, 2);
});
