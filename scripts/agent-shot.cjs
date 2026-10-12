// Sends one message to the stock agent from the page and screenshots the result (dev only).
const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'msedge', headless: true });
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = [];
  p.on('pageerror', (e) => errs.push('PAGE ' + e.message));
  await p.goto((process.argv[3] || 'http://127.0.0.1:8790') + '/');
  await p.waitForTimeout(2000);
  await p.fill('#msg', process.argv[2] || 'Received 12 paneer');
  await p.press('#msg', 'Enter');
  await p.waitForFunction(() => !document.querySelector('.chat .think'), null, { timeout: 120000 });
  await p.waitForTimeout(1200);
  await p.screenshot({ path: 'scripts/shots/agent.png' });
  console.log((await p.locator('#chat').innerText()).slice(-700));
  console.log('errors:', errs.join('\n') || 'none');
  await b.close();
})();
