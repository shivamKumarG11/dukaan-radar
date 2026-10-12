// Dukaan Radar Research Room: workers run real SerpApi searches, Munshi writes the plan.
// Events stream from /api/research (one per search start/finish, then the report).
// Inside the store page (iframe, ?autostart=1) it starts by itself and tells the page when the plan is ready.
import * as THREE from 'three';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const $ = (id) => document.getElementById(id);
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const sleep = (ms) => new Promise((r) => setTimeout(r, reduced ? Math.min(ms, 120) : ms));
let lang = document.documentElement.lang === 'hi' ? 'hi' : 'en';
let lastReport = null, running = false;

const WORKERS = {
  scout: { name: 'Trend Scout', hi: 'ट्रेंड स्काउट', color: '#4fb3e8', x: -7.6, by: 3.6 },
  historian: { name: 'Historian', hi: 'इतिहासकार', color: '#a98bef', x: -2.6, by: 5.0 },
  price: { name: 'Price Checker', hi: 'दाम जाँचक', color: '#5fd39a', x: 2.6, by: 3.6 },
  news: { name: 'News Reader', hi: 'समाचार पाठक', color: '#ff8a65', x: 7.6, by: 5.0 },
};
const MUNSHI = { name: 'Munshi', hi: 'मुंशी', color: '#f2a93b' };
const ACTION = {
  en: { stock_now: 'Order now', last_call: 'Last call', at_peak: 'At peak', cooling: 'Cooling', watch: 'Watch' },
  hi: { stock_now: 'अभी मंगाएँ', last_call: 'आखिरी मौका', at_peak: 'चरम पर', cooling: 'घट रहा', watch: 'नज़र रखें' },
};
const UI = {
  en: { ready: 'READY', searching: 'SEARCHING…', found: 'FOUND', idle: 'Waiting to research the store', title: "Today's stock plan", start: 'Start research', busy: 'Researching…', again: 'Research again', pause: 'Pause', resume: 'Resume', paused: 'PAUSED', board: 'Press Start research', writing: 'WRITING THE PLAN', done: 'PLAN READY' },
  hi: { ready: 'तैयार', searching: 'खोज रहे हैं…', found: 'मिल गया', idle: 'रिसर्च का इंतज़ार', title: 'आज का स्टॉक प्लान', start: 'रिसर्च शुरू करें', busy: 'रिसर्च चल रही है…', again: 'फिर से रिसर्च करें', pause: 'रोकें', resume: 'जारी रखें', paused: 'रुका हुआ', board: 'रिसर्च शुरू करें दबाएँ', writing: 'प्लान लिख रहे हैं', done: 'प्लान तैयार' },
};
const t = (k) => UI[lang][k];
const wname = (w) => (lang === 'hi' ? w.hi : w.name);

// ---------- scene ----------
const host = $('scene');
const scene = new THREE.Scene();
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
renderer.shadowMap.enabled = true;
host.appendChild(renderer.domElement);
const labels = new CSS2DRenderer();
Object.assign(labels.domElement.style, { position: 'absolute', inset: '0', pointerEvents: 'none' });
host.appendChild(labels.domElement);
const camera = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 200);
camera.position.set(13, 14, 19);
camera.lookAt(0, 2.4, -1);

scene.background = new THREE.Color('#1c1512');
scene.add(new THREE.HemisphereLight(0xffe3c2, 0x2a1d16, 0.55));
const lamp = new THREE.PointLight(0xffc27a, 60, 40, 1.6);
lamp.position.set(0, 8, 0.5);
lamp.castShadow = true;
scene.add(lamp);
const key = new THREE.DirectionalLight(0xffd9a8, 0.6);
key.position.set(8, 14, 10);
scene.add(key);

const mat = (c, extra = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, flatShading: true, ...extra });
function box(w, h, d, c, x, y, z, parent = scene) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), typeof c === 'object' ? c : mat(c));
  m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; parent.add(m); return m;
}
box(22, 0.4, 15, '#3a2a20', 0, -0.2, 0.3);                 // floor
box(22, 9.5, 0.4, '#2a1f19', 0, 4.55, -7.2);              // back wall
box(0.4, 9.5, 15, '#241b16', -11.2, 4.55, 0.3);           // left wall
box(6, 0.05, 4, '#5b2f2a', 0, 0.03, 1.8);                 // rug

// chalkboard with a canvas texture Munshi writes on
box(9.8, 4.8, 0.25, '#5a3f2c', 0, 5.2, -6.95);
const boardCanvas = document.createElement('canvas');
boardCanvas.width = 1200; boardCanvas.height = 560;
const boardTex = new THREE.CanvasTexture(boardCanvas);
boardTex.colorSpace = THREE.SRGBColorSpace;
const board = new THREE.Mesh(new THREE.PlaneGeometry(9.2, 4.3), new THREE.MeshStandardMaterial({ map: boardTex, roughness: 1 }));
board.position.set(0, 5.2, -6.8); scene.add(board);
let boardLines = [];

function drawBoard(sub) {
  const g = boardCanvas.getContext('2d');
  g.fillStyle = '#1e2a23'; g.fillRect(0, 0, 1200, 560);
  g.fillStyle = 'rgba(255,255,255,0.04)';
  for (let i = 0; i < 40; i++) g.fillRect(Math.random() * 1200, Math.random() * 560, 60, 2);
  g.fillStyle = '#f4ede4'; g.font = '800 54px "Bricolage Grotesque", sans-serif';
  g.fillText(t('title'), 44, 82);
  g.fillStyle = '#a9bdb0'; g.font = '500 28px Hind, sans-serif';
  g.fillText(sub || (boardLines.length ? '' : t('board')), 46, 126);
  boardLines.forEach((l, i) => {
    const y = 196 + i * 88;
    g.fillStyle = '#f2a93b'; g.font = '800 46px "Bricolage Grotesque", sans-serif'; g.fillText(String(i + 1), 46, y);
    g.fillStyle = '#f4ede4'; g.font = '600 42px Hind, sans-serif'; g.fillText(lang === 'hi' ? l.hi : l.name, 100, y);
    const w = g.measureText(lang === 'hi' ? l.hi : l.name).width;
    g.fillStyle = l.action === 'last_call' ? '#ff8a65' : l.action === 'stock_now' ? '#f2a93b' : '#cfe0d4';
    g.font = '600 34px Hind, sans-serif'; g.fillText('· ' + ACTION[lang][l.action], 120 + w, y);
  });
  boardTex.needsUpdate = true;
}

// people
function person(color, x, z) {
  const grp = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.42, 0.62, 4, 10), mat(color));
  body.position.y = 1.05; body.castShadow = true; grp.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.34, 14, 10), mat('#e8c19a'));
  head.position.y = 2.0; head.castShadow = true; grp.add(head);
  const hair = new THREE.Mesh(new THREE.SphereGeometry(0.35, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat('#2a1d16'));
  hair.position.y = 2.05; grp.add(hair);
  grp.position.set(x, 0, z); scene.add(grp);
  return { grp, body, head };
}
function bubble(w) {
  const el = document.createElement('div');
  el.className = 'bubble idle';
  el.style.setProperty('--c', w.color);
  el.innerHTML = '<span class="st"></span><span class="q"></span>';
  return el;
}
function tag(text, color) {
  const el = document.createElement('div');
  el.className = 'tag'; el.style.color = color; el.textContent = text;
  return el;
}

for (const [id, w] of Object.entries(WORKERS)) {
  box(2.8, 0.16, 1.3, '#6b4a33', w.x, 1.3, 0.9);                                   // desk
  for (const [dx, dz] of [[-1.25, -0.5], [1.25, -0.5], [-1.25, 0.5], [1.25, 0.5]]) box(0.12, 1.22, 0.12, '#4a3324', w.x + dx, 0.61, 0.9 + dz);
  box(1.35, 0.9, 0.08, '#0c0a09', w.x, 1.95, 0.45);                                // monitor
  box(0.12, 0.4, 0.12, '#0c0a09', w.x, 1.55, 0.45);
  w.screen = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 0.76), new THREE.MeshStandardMaterial({ color: '#0c0a09', emissive: w.color, emissiveIntensity: 0.15 }));
  w.screen.position.set(w.x, 1.95, 0.5); scene.add(w.screen);
  w.p = person(w.color, w.x, 2.15);
  w.p.grp.rotation.y = Math.PI;                                                     // faces the desk and the board
  w.bubbleEl = bubble(w);
  const b = new CSS2DObject(w.bubbleEl); b.position.set(w.x, w.by, 2.15); scene.add(b);
  w.tagEl = tag(wname(w), w.color);
  const tg = new CSS2DObject(w.tagEl); tg.position.set(w.x, -0.15, 3.1); scene.add(tg);
  w.mode = 'idle'; w.until = 0; w.id = id;
}
const munshi = person(MUNSHI.color, 5.9, -5.6);
munshi.grp.rotation.y = -0.6;
const mBubble = bubble(MUNSHI);
const mb = new CSS2DObject(mBubble); mb.position.set(5.9, 3.4, -5.6); scene.add(mb);
const mTag = tag(wname(MUNSHI), MUNSHI.color);
const mt = new CSS2DObject(mTag); mt.position.set(5.9, -0.1, -4.6); scene.add(mt);
let munshiMode = 'idle', munshiTarget = 5.9;

function setBubble(el, status, query, idle) {
  el.querySelector('.st').textContent = status;
  el.querySelector('.q').textContent = query;
  el.classList.toggle('idle', !!idle);
}
function resetWorkers() {
  for (const w of Object.values(WORKERS)) { w.mode = 'idle'; w.bubbleEl.classList.add('mini'); setBubble(w.bubbleEl, t('ready'), t('idle'), true); w.tagEl.textContent = wname(w); }
  setBubble(mBubble, t('ready'), lang === 'hi' ? 'सबूत आने पर प्लान लिखूँगा' : 'Writes the plan from the evidence', true);
  mTag.textContent = wname(MUNSHI);
}

function resize() {
  const w = host.clientWidth, h = host.clientHeight;
  renderer.setSize(w, h); labels.setSize(w, h);
  const view = w < 700 ? 13 : 10.5, aspect = w / h;
  Object.assign(camera, { left: -view * aspect, right: view * aspect, top: view, bottom: -view });
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(host);
resize();

const clock = new THREE.Clock();
function frame() {
  const now = clock.getElapsedTime();
  for (const w of Object.values(WORKERS)) {
    const p = w.p;
    if (w.mode === 'working') {
      p.body.position.y = 1.05 + Math.abs(Math.sin(now * 14)) * (reduced ? 0 : 0.05);
      p.head.rotation.x = Math.sin(now * 7) * 0.12;
      w.screen.material.emissiveIntensity = 0.7 + Math.sin(now * 22) * 0.25;
    } else if (w.mode === 'found' && now < w.until) {
      const k = (w.until - now) / 0.6;
      p.grp.position.y = reduced ? 0 : Math.sin(k * Math.PI) * 0.45;
      w.screen.material.emissiveIntensity = 1.1;
    } else {
      if (w.mode === 'found') w.mode = 'rested';
      p.grp.position.y = 0;
      p.body.position.y = 1.05 + Math.sin(now * 1.6 + w.x) * 0.015;
      w.screen.material.emissiveIntensity = w.mode === 'rested' ? 0.45 : 0.15;
    }
  }
  if (munshiMode === 'writing' && !reduced) munshi.grp.position.x += (munshiTarget - munshi.grp.position.x) * 0.06;
  else munshi.grp.position.x += (5.9 - munshi.grp.position.x) * 0.04;
  munshi.body.position.y = 1.05 + (munshiMode === 'writing' ? Math.abs(Math.sin(now * 9)) * 0.04 : 0);
  mb.position.x = munshi.grp.position.x; mt.position.x = munshi.grp.position.x;
  renderer.render(scene, camera); labels.render(scene, camera);
  requestAnimationFrame(frame);
}

// ---------- evidence flights ----------
function toScreen(v3) {
  const v = v3.clone().project(camera);
  return { x: (v.x + 1) / 2 * host.clientWidth, y: (1 - v.y) / 2 * host.clientHeight };
}
function flyCard(worker, title, text) {
  const from = toScreen(new THREE.Vector3(worker.x, 2.6, 2.1));
  const to = toScreen(new THREE.Vector3(-1 + Math.random() * 2, 5.4, -6.8));
  const el = document.createElement('div');
  el.className = 'card';
  el.style.setProperty('--c', worker.color);
  el.style.left = (from.x - 110) + 'px'; el.style.top = (from.y - 30) + 'px';
  el.innerHTML = `<small>${title}</small>${text}`;
  $('fly').appendChild(el);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    el.style.transform = `translate(${to.x - from.x}px, ${to.y - from.y}px) scale(0.55) rotate(${(Math.random() - 0.5) * 8}deg)`;
    el.style.opacity = '0';
  }));
  setTimeout(() => el.remove(), 1400);
}

// ---------- text helpers ----------
function queryText(l) {
  const city = (l.location || '').split(',')[0];
  if (l.engine === 'google_shopping') return `google_shopping · "${l.q}" · ${city}`;
  if (l.engine === 'google_news') return `google_news · ${l.q}`;
  if (l.engine === 'google_maps') return 'google_maps · supermarkets near the store';
  if (l.engine === 'google_trends_trending_now') return 'trending_now · India · last 24 h';
  if (l.data_type === 'GEO_MAP_0') return `google_trends · "${l.q}" · by state`;
  if (l.data_type === 'RELATED_QUERIES') return `google_trends · rising · "${l.q}" · ${l.geo}`;
  if (l.data_type === 'TIMESERIES' && l.date && !String(l.date).startsWith('today')) return `google_trends · last season · ${String(l.q).split(',').join(', ')}`;
  return `google_trends · ${l.geo} · ${String(l.q).split(',').join(', ')}`;
}
function logLine(ev) {
  const w = WORKERS[ev.worker] || WORKERS.scout;
  const li = document.createElement('li');
  li.style.setProperty('--c', w.color);
  const src = ev.source === 'live' ? 'live' : 'cache';
  li.innerHTML = `<i></i><div>${wname(w)}<span>${queryText(ev.label)} · <b class="${src}">${src === 'live' ? 'live' : 'cached'}</b></span></div>`;
  $('log').prepend(li);
}
let counts = { live: 0, cached: 0 };
function meter() { $('meter').textContent = `${counts.live} live · ${counts.cached} cached SerpApi searches`; }

// ---------- event handling ----------
const queue = [];
let pumping = false;
function push(ev) { queue.push(ev); if (!pumping) pump(); }
let paused = false, unpause = null;
async function pump() {
  pumping = true;
  while (queue.length) {
    if (paused) await new Promise((r) => (unpause = r));
    await handle(queue.shift());
  }
  pumping = false;
}
async function handle(ev) {
  if (ev.type === 'search' && ev.phase === 'start') {
    const w = WORKERS[ev.worker] || WORKERS.scout;
    for (const o of Object.values(WORKERS)) o.bubbleEl.classList.toggle('mini', o !== w);  // only the active worker speaks
    w.mode = 'working';
    setBubble(w.bubbleEl, t('searching'), queryText(ev.label), false);
    $('narrate').textContent = `${w.name}: ${queryText(ev.label)}`;
    await sleep(650);
  } else if (ev.type === 'search' && ev.phase === 'done') {
    const w = WORKERS[ev.worker] || WORKERS.scout;
    w.mode = 'found'; w.until = clock.getElapsedTime() + 0.6;
    setBubble(w.bubbleEl, `${t('found')} · ${ev.source === 'live' ? 'live' : 'cached'}`, queryText(ev.label), false);
    ev.source === 'live' ? counts.live++ : counts.cached++;
    meter(); logLine(ev);
    await sleep(300);
  } else if (ev.type === 'report') {
    await writePlan(ev.report);
  } else if (ev.type === 'error') {
    setBubble(mBubble, 'ERROR', ev.message, false);
    finish();
  }
}

function evidence(p, r) {
  const out = [];
  const en = lang !== 'hi';
  if (p.momentum != null) out.push([WORKERS.scout, en ? 'TREND SCOUT' : 'ट्रेंड स्काउट', en ? `${p.momentum}× vs a month ago in ${r.state}` : `${r.state} में एक महीने में ${p.momentum} गुना`]);
  if (p.replay) out.push([WORKERS.historian, en ? 'HISTORIAN' : 'इतिहासकार', en ? `${fmtG(p.replay.growth)}× still ahead last season` : `पिछले साल ${fmtG(p.replay.growth)} गुना और बढ़ा`]);
  if (p.price) out.push([WORKERS.price, en ? 'PRICE CHECKER' : 'दाम जाँचक', en ? `₹${p.price.median.toLocaleString('en-IN')} median online in ${r.city}` : `${r.city} में ऑनलाइन औसत ₹${p.price.median.toLocaleString('en-IN')}`]);
  if (p.news && p.news.length) out.push([WORKERS.news, en ? 'NEWS READER' : 'समाचार पाठक', p.news[0].title.slice(0, 70)]);
  return out;
}
const fmtG = (g) => (g >= 10 ? g.toFixed(0) : g.toFixed(1));

async function writePlan(r) {
  lastReport = r;
  boardLines = [];
  munshiMode = 'writing';
  for (const o of Object.values(WORKERS)) o.bubbleEl.classList.add('mini');
  setBubble(mBubble, t('writing'), `${r.shop_label} · ${r.recs.length} items`, false);
  $('plan').hidden = false;
  $('plan-list').innerHTML = '';
  renderPlanHead(r);
  for (const [i, p] of r.picks.entries()) {
    for (const [w, title, text] of evidence(p, r)) { flyCard(w, title, text); await sleep(260); }
    await sleep(700);
    munshiTarget = -3 + i * 2;
    boardLines.push(p); drawBoard(' ');
    addPlanItem(p, r);
    await sleep(500);
  }
  munshiMode = 'idle';
  setBubble(mBubble, t('done'), lang === 'hi' ? `${r.picks.length} सुझाव, सबूत के साथ` : `${r.picks.length} calls, each with its evidence`, false);
  finish();
  if (window.parent !== window) window.parent.postMessage({ type: 'research-done' }, location.origin);
}

function renderPlanHead(r) {
  $('plan-title').textContent = t('title');
  const a = r.anchor;
  $('plan-sub').textContent = lang === 'hi'
    ? `${r.totals.stock_up} बढ़ाएँ · ${r.totals.restock} भरें · ${a.hi} में ${a.days} दिन`
    : `${r.totals.stock_up} to stock up · ${r.totals.restock} to restock · ${a.name} in ${a.days} days`;
  $('details').href = `/?lang=${lang}`;
}
function addPlanItem(p, r) {
  const li = document.createElement('li');
  const chips = evidence(p, r).map(([w, title]) => `<span class="chip" style="--c:${w.color}">${title.toLowerCase()}</span>`).join('');
  li.innerHTML = `<div class="top"><b>${lang === 'hi' ? p.hi : p.name}</b><span class="badge ${p.action}">${ACTION[lang][p.action]}</span></div>
    <p>${lang === 'hi' ? p.action_hi : p.action_en}</p><div class="chips">${chips}</div>`;
  $('plan-list').appendChild(li);
  shareLink(r);
}
function shareLink(r) {
  const lines = r.picks.slice(0, $('plan-list').children.length).map((p, i) => `${i + 1}. ${lang === 'hi' ? p.hi : p.name}: ${lang === 'hi' ? p.action_hi : p.action_en}`);
  const head = lang === 'hi' ? `${r.shop_label} · आज का स्टॉक प्लान` : `${r.shop_label} · Today's stock plan`;
  $('share').href = 'https://wa.me/?text=' + encodeURIComponent([head, ...lines].join('\n'));
}
function rerenderPlan() {
  if (!lastReport) return;
  $('plan-list').innerHTML = '';
  renderPlanHead(lastReport);
  lastReport.picks.forEach((p) => addPlanItem(p, lastReport));
  drawBoard(' ');
}

// ---------- controls ----------
let source = null;
function setPaused(v) {
  paused = v;
  $('pause').setAttribute('aria-pressed', String(v));
  $('pause').textContent = v ? t('resume') : t('pause');
  if (v) setBubble(mBubble, t('paused'), lang === 'hi' ? 'जारी रखें दबाएँ' : 'Press Resume to carry on', false);
  else { setBubble(mBubble, t('ready'), lang === 'hi' ? 'सबूत आने पर प्लान लिखूँगा' : 'Writes the plan from the evidence', true); if (unpause) { unpause(); unpause = null; } }
  fetch('/api/research/pause', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paused: v }) }).catch(() => {});
}
$('pause').onclick = () => setPaused(!paused);
function finish() {
  running = false;
  $('pause').hidden = true; paused = false;
  if (source) { source.close(); source = null; }
  $('go').disabled = false; $('go').textContent = t('again');
}
$('pick').addEventListener('submit', (e) => {
  e.preventDefault();
  if (running) return;
  running = true;
  $('go').disabled = true; $('go').textContent = t('busy');
  $('pause').hidden = false; $('pause').textContent = t('pause'); $('pause').setAttribute('aria-pressed', 'false');
  $('hint').hidden = true;
  $('log').innerHTML = ''; $('plan').hidden = true;
  counts = { live: 0, cached: 0 }; meter();
  boardLines = []; drawBoard(lang === 'hi' ? 'कर्मचारी खोज रहे हैं…' : 'The workers are researching…');
  resetWorkers();
  source = new EventSource('/api/research');
  source.onmessage = (m) => {
    const ev = JSON.parse(m.data);
    if (ev.type === 'report' || ev.type === 'error') { source.close(); source = null; }  // no auto-reconnect: a rerun would spend searches
    push(ev);
  };
  source.onerror = () => { if (source) { source.close(); source = null; push({ type: 'error', message: 'Connection lost' }); } };
});
function setLang(l) {
  lang = l;
  document.documentElement.lang = l;
  $('lang-en').setAttribute('aria-pressed', String(l === 'en'));
  $('lang-hi').setAttribute('aria-pressed', String(l === 'hi'));
  if (!running) { $('go').textContent = lastReport ? t('again') : t('start'); resetWorkers(); }
  for (const w of Object.values(WORKERS)) w.tagEl.textContent = wname(w);
  mTag.textContent = wname(MUNSHI);
  rerenderPlan();
  if (!lastReport) drawBoard();
}
$('lang-en').onclick = () => setLang('en');
$('lang-hi').onclick = () => setLang('hi');

document.fonts.ready.then(() => drawBoard());
drawBoard();
resetWorkers();
$('go').textContent = t('start');
meter();
requestAnimationFrame(frame);
if (new URLSearchParams(location.search).get('autostart') === '1') $('pick').requestSubmit();
