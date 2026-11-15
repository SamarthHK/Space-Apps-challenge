import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseApiOrigin } from '../src/config.js';
import { ApiError, createClient } from '../src/api/client.js';
import { createResource } from '../src/state/resource.js';

const envelope = data => ({ data, meta: { api_version: 'v1', request_id: 'transport-test' } });

test('origin configuration rejects paths, secrets, public hosts and wildcards', () => {
  for (const value of ['', undefined, 'http://0.0.0.0:8000', 'http://example.com',
    'http://user:secret@localhost', 'http://localhost/api/v1', 'http://localhost?x=1',
    'http://localhost#x', 'ftp://localhost', 'http://localhost:0', 'http://100.128.1.1']) {
    assert.throws(() => parseApiOrigin(value));
  }
  assert.equal(parseApiOrigin('http://localhost:8000/'), 'http://localhost:8000');
  assert.equal(parseApiOrigin('http://100.64.0.1:8000'), 'http://100.64.0.1:8000');
});

test('requests use exactly one API prefix, encoded filters and no credentials', async () => {
  const client = createClient('http://localhost:8000', { fetcher: async (url, options) => {
    assert.equal(url.pathname, '/api/v1/fields');
    assert.equal(url.searchParams.get('cursor'), 'a/b+&c');
    assert.equal(url.searchParams.has('empty'), false);
    assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error');
    assert.equal(options.cache, 'no-store');
    return Response.json(envelope([]));
  } });
  assert.deepEqual((await client.get('/fields', { params: { cursor: 'a/b+&c', empty: null } })).data, []);
  await assert.rejects(client.get('//example.com'), { code: 'invalid_path' });
});

test('server failures, malformed JSON and invalid success schemas stay distinct', async () => {
  const cases = [
    [() => Response.json({ error: { code: 'data_unavailable', message: 'Not configured' } }, { status: 503 }), 'data_unavailable'],
    [() => new Response('<html>proxy failed</html>', { status: 502 }), 'malformed_response'],
    [() => Response.json({ data: [] }), 'invalid_response'],
    [() => { throw new TypeError('network'); }, 'network_error'],
  ];
  for (const [fetcher, code] of cases) {
    await assert.rejects(createClient('http://localhost:8000', { fetcher }).get('/fields'),
      error => error instanceof ApiError && error.code === code);
  }
  await assert.rejects(createClient('http://localhost:8000', {
    fetcher: async () => Response.json(envelope({})), validate: () => false,
  }).get('/fields', { schema: 'FieldsResponse' }), { code: 'invalid_response' });
});

test('timeout and superseded requests abort without retrying', async () => {
  let calls = 0;
  const fetcher = (_, { signal }) => new Promise((resolve, reject) => {
    calls++;
    if (signal.aborted) reject(new DOMException('Aborted', 'AbortError'));
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  });
  const client = createClient('http://localhost:8000', { fetcher, timeoutMs: 10 });
  await assert.rejects(client.get('/fields'), { code: 'timeout' });
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(client.get('/fields', { signal: controller.signal }), { code: 'aborted' });
  assert.equal(calls, 2);
});

test('late responses and errors cannot overwrite newer field state', async () => {
  const resource = createResource();
  let finishOld;
  const old = resource.load('old', () => new Promise(resolve => { finishOld = resolve; }));
  await resource.load('new', async () => envelope([]));
  finishOld(envelope({ stale: true }));
  await old;
  assert.equal(resource.state.requestKey, 'new');
  assert.equal(resource.state.status, 'empty');
  await resource.load('failed', async () => { throw new ApiError('network_error', 'Offline'); });
  assert.equal(resource.state.status, 'error');
  assert.equal(resource.state.data, null);
  resource.clear();
  assert.equal(resource.state.status, 'idle');
});

test('clearing a resource prevents in-flight completion from restoring data', async () => {
  const resource = createResource();
  let complete;
  const pending = resource.load('field', () => new Promise(resolve => { complete = resolve; }));
  resource.clear();
  complete(envelope({}));
  await pending;
  assert.equal(resource.state.data, null);
});

test('conditional writes preserve ETags and field errors without credentials or retry', async () => {
  let calls = 0;
  const client = createClient('http://localhost:8000', { fetcher: async (_, options) => {
    calls++;
    assert.equal(options.method, 'PATCH');
    assert.equal(options.headers['If-Match'], '"profile:shared:1"');
    assert.equal(options.headers['Content-Type'], 'application/json');
    assert.equal(options.credentials, 'omit');
    assert.deepEqual(JSON.parse(options.body), { name: null });
    return Response.json(envelope({ version: 2 }), { headers: { ETag: '"profile:shared:2"' } });
  } });
  const result = await client.request('/profile', { method: 'PATCH', body: { name: null },
    headers: { 'If-Match': '"profile:shared:1"' } });
  assert.equal(result.etag, '"profile:shared:2"');
  assert.equal(calls, 1);
  const failing = createClient('http://localhost:8000', { fetcher: async () => Response.json({
    error: { code: 'validation_error', message: 'Invalid profile', retryable: false,
      details: [{ path: 'body.phone', code: 'value_error', message: 'Invalid phone' }] },
  }, { status: 422 }) });
  await assert.rejects(failing.request('/profile', { method: 'PATCH', body: {} }), error =>
    error.details[0].path === 'body.phone' && !error.outcomeUncertain);
});

test('lost write responses are ambiguous and are never replayed', async () => {
  let calls = 0;
  const client = createClient('http://localhost:8000', { fetcher: async () => {
    calls++;
    throw new TypeError('Connection lost');
  } });
  await assert.rejects(client.request('/profile', { method: 'PATCH', body: { name: null } }),
    error => error.outcomeUncertain && error.code === 'network_error');
  assert.equal(calls, 1);
});
