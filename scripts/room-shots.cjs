// Drives the Research Room: start research, screenshot mid-run and at the end (dev only).
const { chromium } = require('playwright-core');
(async () => {
  const base = process.argv[2] || 'http://127.0.0.1:8790';
  const b = await chromium.launch({ channel: 'msedge', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1440, height: 860 } });
  const errs = [];
  p.on('pageerror', (e) => errs.push('PAGE ' + e.message));
  p.on('console', (m) => { if (m.type() === 'error') errs.push('CONSOLE ' + m.text()); });
  await p.goto(base + '/?city=' + (process.argv[3] || 'pune') + '&shop=' + (process.argv[4] || 'gifts'));
  await p.waitForTimeout(2500);
  await p.screenshot({ path: 'scripts/shots/room-0-idle.png' });
  await p.click('#go');
  await p.waitForTimeout(6000);
  await p.screenshot({ path: 'scripts/shots/room-1-research.png' });
  await p.waitForFunction(() => /again|फिर/.test(document.getElementById('go').textContent), null, { timeout: 120000 });
  await p.waitForTimeout(1500);
  await p.screenshot({ path: 'scripts/shots/room-2-plan.png' });
  console.log('meter:', await p.locator('#meter').innerText());
  console.log('plan:', (await p.locator('#plan-list').innerText()).replace(/\n/g, ' | ').slice(0, 400));
  await p.click('#lang-hi'); await p.waitForTimeout(1200);
  await p.screenshot({ path: 'scripts/shots/room-3-hindi.png' });
  console.log(errs.length ? errs.join('\n') : 'no page errors');
  await b.close();
})();
