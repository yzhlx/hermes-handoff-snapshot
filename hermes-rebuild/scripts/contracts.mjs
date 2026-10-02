import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import openapiTS, { astToString } from 'openapi-typescript';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const api = resolve(root, 'apps/api');
const target = resolve(root, 'packages/contracts');
const scratch = await mkdtemp(resolve(tmpdir(), 'hermes-contract-'));
const check = process.argv.includes('--check');
try {
  const exported = resolve(scratch, 'openapi.json');
  const result = spawnSync('uv', [
    'run', '--project', api, '--frozen', 'python', '-m', 'hermes_api.cli',
    'export-openapi', '--output', exported,
  ], { cwd: api, encoding: 'utf8', env: { ...process.env, UV_CACHE_DIR: resolve(api, '.uv-cache') } });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`OpenAPI export failed: ${result.stderr}`);
  const spec = JSON.parse(await readFile(exported, 'utf8'));
  const openapi = `${JSON.stringify(spec, null, 2)}\n`;
  const schema = astToString(await openapiTS(spec, { alphabetize: true }));
  const outputs = [
    [resolve(api, 'openapi.json'), openapi],
    [resolve(target, 'openapi.json'), openapi],
    [resolve(target, 'src/schema.d.ts'), schema],
  ];
  for (const [name, content] of outputs) {
    const path = name;
    if (check) {
      let current;
      try { current = await readFile(path, 'utf8'); }
      catch { throw new Error(`Missing generated contract ${name}; run pnpm contracts:generate`); }
      if (current.replaceAll('\r\n', '\n') !== content.replaceAll('\r\n', '\n')) {
        throw new Error(`Contract drift in ${name}; run pnpm contracts:generate and review the change`);
      }
    } else {
      await mkdir(dirname(path), { recursive: true });
      await writeFile(path, content);
    }
  }
  console.log(check ? 'PASS: API and generated TypeScript contracts agree' : 'Generated OpenAPI and TypeScript contracts');
} finally {
  await rm(scratch, { recursive: true, force: true });
}
