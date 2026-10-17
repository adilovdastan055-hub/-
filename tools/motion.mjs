// Рендер HTML/CSS-анимации в PNG-кадры с прозрачностью через Chromium (Playwright).
// usage: node motion.mjs <spec.json>
// spec: { template, width, height, fps, duration, params, outDir }
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require(path.join(process.env.NODE_TOOLS || '/opt/node-tools', 'node_modules/playwright'))); }

const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const { width, height, fps, duration, params = {}, outDir } = spec;
const tpl = spec.template.endsWith('.html') ? path.resolve(spec.template)
  : path.join(path.dirname(new URL(import.meta.url).pathname), 'motion', `${spec.template}.html`);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
await page.addInitScript(p => { window.PARAMS = p; }, { ...params, duration, _w: width, _h: height });
await page.goto('file://' + tpl);
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => window.setup && window.setup());
fs.mkdirSync(outDir, { recursive: true });
const n = Math.round(duration * fps);
for (let i = 0; i < n; i++) {
  const t = i / fps;
  await page.evaluate(t => {
    for (const a of document.getAnimations()) { a.pause(); a.currentTime = t * 1000; }
    window.seek && window.seek(t);
  }, t);
  await page.screenshot({ path: path.join(outDir, `f_${String(i).padStart(5, '0')}.png`), omitBackground: true });
}
await browser.close();
