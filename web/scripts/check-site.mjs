import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Validate the generated output, including fragment links and downloaded assets.
// No network is needed. BASE_PATH must match the value used for the build.
const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const base = '/' + (process.env.BASE_PATH || '/').split('/').filter(Boolean).join('/');
const errors = [];
const pages = new Map();
const allFiles = new Set();
async function visit(folder) {
  for (const entry of await readdir(folder, { withFileTypes: true })) {
    const file = path.join(folder, entry.name);
    if (entry.isDirectory()) await visit(file);
    else {
      const relative = path.relative(dist, file).split(path.sep).join('/');
      allFiles.add(relative);
      if (file.endsWith('.html')) pages.set(relative, await readFile(file, 'utf8'));
    }
  }
}
try { await stat(dist); } catch { throw new Error('Build the site with npm run build before running npm run check.'); }
await visit(dist);
const decode = (text) => text.replaceAll('&amp;', '&').replaceAll('&#39;', "'").replaceAll('&quot;', '"');
let checked = 0;
for (const [file, html] of pages) {
  const pathname = '/' + (base === '/' ? '' : base.slice(1) + '/') + file.replace(/index\.html$/, '');
  if (!/<html[^>]+lang="en"/.test(html)) errors.push(`${file}: missing English language attribute`);
  if (!/<meta\s+name="description"\s+content="[^"]+"/.test(html)) errors.push(`${file}: missing page description`);
  if ((html.match(/<h1[\s>]/g) || []).length !== 1) errors.push(`${file}: expected one h1`);
  for (const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
    const raw = decode(match[1]);
    if (/^(?:https?:|mailto:|tel:|data:|javascript:)/i.test(raw)) continue;
    const url = new URL(raw, `https://docs.invalid${pathname}`);
    if (url.origin !== 'https://docs.invalid') continue;
    if (base !== '/' && url.pathname !== base && !url.pathname.startsWith(base + '/')) {
      errors.push(`${file}: link escapes BASE_PATH: ${raw}`);
      continue;
    }
    let target = decodeURIComponent(url.pathname.slice(base === '/' ? 1 : base.length + 1));
    if (!target || target.endsWith('/')) target += 'index.html';
    if (!allFiles.has(target)) {
      errors.push(`${file}: missing target ${raw} (${target})`);
      continue;
    }
    checked++;
    if (url.hash && pages.has(target)) {
      const id = decodeURIComponent(url.hash.slice(1));
      const ids = [...pages.get(target).matchAll(/\bid="([^"]+)"/g)].map((item) => decode(item[1]));
      if (!ids.includes(id)) errors.push(`${file}: missing fragment ${raw}`);
    }
  }
}
if (![...allFiles].some((file) => file.endsWith('pagefind.js'))) errors.push('Production search index is missing.');
if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
else console.log(`Checked ${pages.size} HTML pages and ${checked} internal links/assets, including fragments and the search index.`);
