import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const backend = process.argv[2];
if (!backend) throw new Error('Usage: node scripts\\pin-contract.js <backend-checkout>');
const root = resolve(backend);
const prefix = execFileSync('git', ['-C', root, 'rev-parse', '--show-prefix'], { encoding: 'utf8' }).trim();
execFileSync('git', ['-C', root, 'diff', '--quiet', 'HEAD', '--', 'docs/openapi.json']);
const backendCommit = execFileSync('git', ['-C', root, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
const bytes = execFileSync('git', ['-C', root, 'show', `${backendCommit}:${prefix}docs/openapi.json`]);
const contract = JSON.parse(bytes);
if (!contract.paths['/api/v1/workspace'] || !contract.components.schemas.WorkspaceResponse) {
  throw new Error('Not a workspace API contract');
}
const revisionSchema = contract.components.schemas.Workspace.properties.contract_revision;
const revisions = revisionSchema.const ? [revisionSchema.const] : revisionSchema.enum;
if (!Array.isArray(revisions) || !revisions.length || revisions.some(value => typeof value !== 'string')) {
  throw new Error('The workspace contract must declare its supported revisions');
}
writeFileSync(new URL('../contracts/openapi.json', import.meta.url), bytes);
writeFileSync(new URL('../contracts/source.json', import.meta.url), JSON.stringify({
  sha256: createHash('sha256').update(bytes).digest('hex'),
  revision: revisions.at(-1), supported_revisions: revisions, backend_commit: backendCommit,
  artifact_path: `${prefix}docs/openapi.json`,
}, null, 2) + '\n');
console.log(`Pinned workspace contract from ${backendCommit}`);
