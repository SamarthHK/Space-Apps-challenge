import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { validateResponse } from '../src/api/validation.js';

test('pinned OpenAPI bytes match recorded backend artifact checksum', async () => {
  const bytes = await readFile(new URL('../contracts/openapi.json', import.meta.url));
  const source = JSON.parse(await readFile(new URL('../contracts/source.json', import.meta.url)));
  assert.equal(createHash('sha256').update(bytes).digest('hex'), source.sha256);
});

test('shared/private workspace and pagination are validated before rendering', () => {
  const meta = { api_version: 'v1', request_id: 'contract-test' };
  const data = { access_mode: 'shared_trusted_network', contract_revision: 'shared-workspace-1',
    project_ids: [], capabilities: [] };
  assert.equal(validateResponse('WorkspaceResponse', { data, meta }), true);
  assert.equal(validateResponse('WorkspaceResponse', {
    data: { ...data, access_mode: 'private_account', contract_revision: 'private-workspace-2' }, meta,
  }), true);
  assert.equal(validateResponse('WorkspaceResponse', { data: { ...data, access_mode: 'private' }, meta }), false);
  assert.equal(validateResponse('FieldsResponse', { data: [], meta }), false);
  assert.equal(validateResponse('FieldsResponse', { data: [], meta: { ...meta, next_cursor: null } }), true);
  assert.equal(validateResponse('FieldsResponse', {
    data: [{ field_id: 'incomplete-transport-record' }], meta: { ...meta, next_cursor: null },
  }), false);
});
