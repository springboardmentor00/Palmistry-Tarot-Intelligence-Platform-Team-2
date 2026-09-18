import { cp, mkdir, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';

await rm('dist', { recursive: true, force: true });
await mkdir('dist', { recursive: true });
await cp('index.html', 'dist/index.html');
await cp('api-bridge.js', 'dist/api-bridge.js');
execFileSync(process.execPath, ['--check', 'api-bridge.js'], { stdio: 'inherit' });
console.log('Static frontend build completed: dist/index.html + dist/api-bridge.js');
