import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

test('contract pinning works in standalone and nested repositories and refuses dirty artifacts', () => {
  const root = mkdtempSync(join(tmpdir(), 'bhumi-contract-'));
  try {
    const frontend = join(root, 'frontend');
    mkdirSync(join(frontend, 'scripts'), { recursive: true });
    mkdirSync(join(frontend, 'contracts'));
    const script = join(frontend, 'scripts', 'pin-contract.js');
    copyFileSync(new URL('../scripts/pin-contract.js', import.meta.url), script);
    writeFileSync(join(frontend, 'package.json'), '{"type":"module"}');
    const bytes = readFileSync(new URL('../contracts/openapi.json', import.meta.url));
    for (const nested of [false, true]) {
      const repository = join(root, nested ? 'combined repo' : 'standalone repo');
      const backend = nested ? join(repository, 'backend') : repository;
      mkdirSync(join(backend, 'docs'), { recursive: true });
      const artifact = join(backend, 'docs', 'openapi.json');
      writeFileSync(artifact, bytes);
      const git = (...args) => execFileSync('git', ['-C', repository, ...args], { stdio: 'pipe' });
      git('init', '--quiet');
      git('add', '.');
      git('-c', 'user.name=Contract test', '-c', 'user.email=contract@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify', '-m',
        'Contract fixture\n\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>');
      execFileSync(process.execPath, [script, backend], { stdio: 'pipe' });
      assert.deepEqual(readFileSync(join(frontend, 'contracts', 'openapi.json')), bytes);
      const pin = JSON.parse(readFileSync(join(frontend, 'contracts', 'source.json')));
      assert.equal(pin.backend_commit, git('rev-parse', 'HEAD').toString().trim());
      assert.equal(pin.artifact_path, `${nested ? 'backend/' : ''}docs/openapi.json`);
      writeFileSync(artifact, '{}\n');
      assert.throws(() => execFileSync(process.execPath, [script, backend], { stdio: 'pipe' }));
      assert.deepEqual(readFileSync(join(frontend, 'contracts', 'openapi.json')), bytes);
    }
  } finally { rmSync(root, { recursive: true, force: true }); }
});
