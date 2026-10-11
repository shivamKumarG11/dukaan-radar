// Screenshots of the running app (dev only): node scripts/shots.cjs [base]
const { chromium } = require('playwright-core');
(async () => {
  const base = process.argv[2] || 'http://127.0.0.1:8770';
  const b = await chromium.launch({ channel: 'msedge', headless: true });
  const errs = [];
  for (const [name, path, w, h] of [['dash-en', '/?city=pune&shop=gifts&lang=en&day=2026-10-11', 1440, 1000], ['dash-hi', '/?city=pune&shop=gifts&lang=hi&day=2026-10-11', 1440, 1000], ['brief', '/brief?city=pune&shop=gifts&day=2026-10-11', 400, 860], ['dash-mobile', '/?city=pune&shop=gifts&lang=en&day=2026-10-11', 390, 844]]) {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    p.on('pageerror', (e) => errs.push(name + ': ' + e.message));
    const r = await p.goto(base + path);
    await p.waitForTimeout(1500);
    await p.screenshot({ path: `scripts/shots/${name}.png`, fullPage: true });
    console.log(name, r.status());
  }
  console.log(errs.length ? errs.join('\n') : 'no page errors');
  await b.close();
})();
