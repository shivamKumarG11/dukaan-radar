const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'msedge', headless: true });
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:8790/'); await p.waitForTimeout(2500);
  await p.screenshot({ path: 'scripts/shots/q-top.png' });
  await p.click('#cats button[data-cat="Festive & pooja"]'); await p.waitForTimeout(1500);
  await p.evaluate(() => scrollTo(0, 480)); await p.waitForTimeout(800);
  await p.screenshot({ path: 'scripts/shots/q-fest.png' });
  await b.close();
})();
