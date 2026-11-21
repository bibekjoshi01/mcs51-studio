import { readFile, writeFile, copyFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const web = fileURLToPath(new URL('../', import.meta.url));
const root = path.dirname(web.replace(/\/$/, ''));
const metadata = await readFile(path.join(root, 'src/mcs51_studio/metadata.py'), 'utf8');
const version = metadata.match(/^VERSION = "([^"]+)"/m)?.[1];
if (!version) throw new Error('Could not find the application version.');
await mkdir(path.join(web, 'src/data'), { recursive: true });
await writeFile(path.join(web, 'src/data/app.json'), JSON.stringify({ version }, null, 2) + '\n');
await copyFile(path.join(root, 'src/mcs51_studio/data/isa.json'), path.join(web, 'src/data/isa.json'));
await copyFile(path.join(root, 'src/mcs51_studio/data/led_counter.asm'), path.join(web, 'public/examples/led-counter.asm'));
await copyFile(path.join(root, 'docs/images/dashboard.png'), path.join(web, 'src/assets/workbench.png'));
await copyFile(path.join(root, 'packaging/icons/mcs51-studio.svg'), path.join(web, 'src/assets/logo.svg'));
await copyFile(path.join(root, 'packaging/icons/mcs51-studio.svg'), path.join(web, 'public/favicon.svg'));
console.log(`Synced application assets and instruction catalog for v${version}.`);
