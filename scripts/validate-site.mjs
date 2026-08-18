import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';

const files = ['index.html', 'admin.html', 'history.html'];
const required = ['firebase-config.js', 'firestore.rules', 'storage.rules'];
const errors = [];

for (const file of [...files, ...required]) {
  if (!fs.existsSync(file)) errors.push(`Missing required file: ${file}`);
}

for (const file of files) {
  if (!fs.existsSync(file)) continue;
  const html = fs.readFileSync(file, 'utf8');

  if (html.includes('<<<<<<<') || html.includes('=======') || html.includes('>>>>>>>')) {
    errors.push(`${file}: unresolved merge-conflict markers found`);
  }

  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map(m => m[1]);
  scripts.forEach((code, index) => {
    const temp = path.join(os.tmpdir(), `oregono-${process.pid}-${index}.mjs`);
    try {
      fs.writeFileSync(temp, code, 'utf8');
      execFileSync(process.execPath, ['--check', temp], { stdio: 'pipe' });
    } catch (error) {
      const message = error?.stderr?.toString().trim() || error.message;
      errors.push(`${file}#script-${index + 1}: ${message}`);
    } finally {
      try { fs.unlinkSync(temp); } catch {}
    }
  });

  const openHtml = (html.match(/<html\b/gi) || []).length;
  const closeHtml = (html.match(/<\/html>/gi) || []).length;
  const openBody = (html.match(/<body\b/gi) || []).length;
  const closeBody = (html.match(/<\/body>/gi) || []).length;
  if (openHtml !== 1 || closeHtml !== 1) errors.push(`${file}: expected exactly one <html> and </html>`);
  if (openBody !== 1 || closeBody !== 1) errors.push(`${file}: expected exactly one <body> and </body>`);
}

if (errors.length) {
  console.error('\nSite validation failed:\n- ' + errors.join('\n- '));
  process.exit(1);
}

console.log('Site validation passed.');
