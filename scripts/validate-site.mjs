import fs from 'node:fs';
import vm from 'node:vm';

const files = ['index.html', 'admin.html', 'history.html', 'stream-control.html'];
const required = ['firebase-config.js', 'firestore.rules', 'storage.rules'];
const errors = [];

function read(path) {
  if (!fs.existsSync(path)) {
    errors.push(`Missing required file: ${path}`);
    return '';
  }
  return fs.readFileSync(path, 'utf8');
}

for (const path of [...files, ...required]) read(path);

for (const path of files) {
  if (!fs.existsSync(path)) continue;
  const html = fs.readFileSync(path, 'utf8');

  if (html.includes('<<<<<<<') || html.includes('=======') || html.includes('>>>>>>>')) {
    errors.push(`${path}: unresolved merge-conflict markers found`);
  }

  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map(m => m[1]);
  scripts.forEach((code, index) => {
    try {
      // Syntax-only validation. Browser globals/imports are intentionally not executed.
      new vm.Script(code, { filename: `${path}#script-${index + 1}` });
    } catch (error) {
      errors.push(`${path}#script-${index + 1}: ${error.message}`);
    }
  });

  const openHtml = (html.match(/<html\b/gi) || []).length;
  const closeHtml = (html.match(/<\/html>/gi) || []).length;
  const openBody = (html.match(/<body\b/gi) || []).length;
  const closeBody = (html.match(/<\/body>/gi) || []).length;
  if (openHtml !== 1 || closeHtml !== 1) errors.push(`${path}: expected exactly one <html> and </html>`);
  if (openBody !== 1 || closeBody !== 1) errors.push(`${path}: expected exactly one <body> and </body>`);
}

if (errors.length) {
  console.error('\nSite validation failed:\n- ' + errors.join('\n- '));
  process.exit(1);
}

console.log('Site validation passed.');
