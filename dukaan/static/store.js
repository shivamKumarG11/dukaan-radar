// Dukaan Radar store page: stock grid, research results on every item, the stock agent.
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const rupees = (n) => '₹' + Math.round(n).toLocaleString('en-IN');
let lang = window.DR.lang;
let state = { items: [], research: null, summary: null };
let cat = 'All', onlyAction = false, chat = [];

const T = {
  en: {
    tagline: 'Stock radar', run: 'Run demand research', near_empty: 'Nearby supermarkets appear after research (Google Maps via SerpApi).',
    k_items: 'Items', k_value: 'Stock value', k_value_sub: 'at cost price', k_low: 'Running low',
    plan_empty_title: 'No research yet', plan_empty: 'Press Run demand research. Four workers check the 6 key festive-season items against live Google Trends, Shopping and News data for Mumbai, and every item gets a stock check.',
    apply: 'Apply all orders', replay: 'Watch the research', stock: 'Stock', f_all: 'All', f_act: 'Needs action', add: '+ Add item', reset: 'Reset demo stock',
    agent: 'Stock agent', agent_sub: 'Changes stock, reads the research, checks live prices and news',
    close_busy: 'Researching… back to the store', close_done: 'See the plan in the store', cancel: 'Cancel', save: 'Save',
    fl_name: 'Name', fl_hindi: 'Hindi name', fl_cat: 'Category', fl_unit: 'Unit', fl_qty: 'In stock', fl_reorder: 'Normal weekly stock', fl_cost: 'Cost ₹', fl_price: 'Price ₹', fl_term: 'What people Google for it',
    all: 'All', search: 'Search items', msg: 'Ask or tell the agent…', add_title: 'Add item', edit_title: 'Edit item',
    up: (n) => `Stock up +${n}`, re: (n) => `Restock +${n}`, slow: 'Slow down', ok: 'OK', done: 'Stocked ✓',
    t_up: (n) => `${n} stock up`, t_re: (n) => `${n} restock`, t_slow: (n) => `${n} slow down`,
    t_order: (u, s) => `Order <b>${u} units</b> for about <b>${s}</b> to be ready for the festival rush.`,
    t_none: 'All recommended orders are in stock. ✓',
    t_when: (d, n) => `Research of ${d} · ${n} SerpApi searches`, normal: (n, u) => `of ${n} normal<br>${esc(u)}`,
    diwali: 'Diwali', days: (n) => `${n} days`, fest_sub: (f, n) => n === 0 ? `${f} today` : `${f} in ${n} days`,
    cats: (n) => `${n} categories`, none_low: 'all fine', thinking: 'Working…', del: (n) => `Remove ${n} from the stock?`,
    applied: (n) => `${n} orders received into stock`, nothing: 'Nothing left to order', ready: 'Research ready: recommendations are on every item',
    reset_q: 'Put the 50 demo items back as they were?', searches_left: (n) => `${n} SerpApi searches left`, empty: 'No items here.',
    hello: 'Namaste! I manage the stock here. Tell me what came in or went out, or ask what to order. I use the latest research and live Google Shopping and News.',
    suggest: ['What is running low?', 'What should I stock up for Diwali?', 'Received 12 paneer', 'Check the online price of ghee', 'Any news on edible oil prices?'],
  },
  hi: {
    tagline: 'स्टॉक रडार', run: 'मांग की रिसर्च करें', near_empty: 'रिसर्च के बाद आस-पास के सुपरमार्केट दिखेंगे (SerpApi से Google Maps)।',
    k_items: 'सामान', k_value: 'स्टॉक की कीमत', k_value_sub: 'लागत पर', k_low: 'कम बचा',
    plan_empty_title: 'अभी रिसर्च नहीं हुई', plan_empty: '"मांग की रिसर्च करें" दबाएँ। चार कर्मचारी त्योहार के 6 खास सामान को मुंबई के लाइव Google Trends, Shopping और News डेटा से जाँचेंगे, और हर सामान का स्टॉक देखा जाएगा।',
    apply: 'सारे ऑर्डर लगाएँ', replay: 'रिसर्च देखें', stock: 'स्टॉक', f_all: 'सभी', f_act: 'ध्यान दें', add: '+ सामान जोड़ें', reset: 'डेमो स्टॉक वापस',
    agent: 'स्टॉक एजेंट', agent_sub: 'स्टॉक बदलता है, रिसर्च पढ़ता है, लाइव दाम और खबरें देखता है',
    close_busy: 'रिसर्च चल रही है… दुकान पर वापस', close_done: 'दुकान में प्लान देखें', cancel: 'रद्द करें', save: 'सेव करें',
    fl_name: 'नाम', fl_hindi: 'हिंदी नाम', fl_cat: 'श्रेणी', fl_unit: 'यूनिट', fl_qty: 'स्टॉक में', fl_reorder: 'सामान्य साप्ताहिक स्टॉक', fl_cost: 'लागत ₹', fl_price: 'दाम ₹', fl_term: 'लोग Google पर क्या खोजते हैं',
    all: 'सभी', search: 'सामान खोजें', msg: 'एजेंट से पूछें या कहें…', add_title: 'सामान जोड़ें', edit_title: 'सामान बदलें',
    up: (n) => `स्टॉक बढ़ाएँ +${n}`, re: (n) => `फिर भरें +${n}`, slow: 'कम मंगाएँ', ok: 'ठीक है', done: 'भर गया ✓',
    t_up: (n) => `${n} बढ़ाएँ`, t_re: (n) => `${n} फिर भरें`, t_slow: (n) => `${n} कम मंगाएँ`,
    t_order: (u, s) => `त्योहार की भीड़ के लिए <b>${u} यूनिट</b> मंगाएँ, करीब <b>${s}</b>।`,
    t_none: 'सुझाए गए सारे ऑर्डर स्टॉक में हैं। ✓',
    t_when: (d, n) => `${d} की रिसर्च · ${n} SerpApi खोजें`, normal: (n, u) => `सामान्य ${n} में से<br>${esc(u)}`,
    diwali: 'दिवाली', days: (n) => `${n} दिन`, fest_sub: (f, n) => n === 0 ? `आज ${f}` : `${f} में ${n} दिन`,
    cats: (n) => `${n} श्रेणियाँ`, none_low: 'सब ठीक', thinking: 'काम चल रहा है…', del: (n) => `${n} को स्टॉक से हटाएँ?`,
    applied: (n) => `${n} ऑर्डर स्टॉक में आ गए`, nothing: 'मंगाने को कुछ नहीं बचा', ready: 'रिसर्च तैयार: हर सामान पर सुझाव है',
    reset_q: '50 डेमो सामान पहले जैसे कर दें?', searches_left: (n) => `${n} SerpApi खोजें बाकी`, empty: 'यहाँ कोई सामान नहीं।',
    hello: 'नमस्ते! मैं इस दुकान का स्टॉक संभालता हूँ। बताइए क्या आया या बिका, या पूछिए क्या मंगाना है। मैं ताज़ा रिसर्च और लाइव Google Shopping व News देखता हूँ।',
    suggest: ['क्या कम बचा है?', 'दिवाली के लिए क्या ज़्यादा मंगाऊँ?', '12 पनीर आ गए', 'घी का ऑनलाइन दाम देखो', 'खाने के तेल के दाम की कोई खबर?'],
  },
};
const t = (k, ...a) => (typeof T[lang][k] === 'function' ? T[lang][k](...a) : T[lang][k]);
const CAT_HI = { 'Staples': 'राशन', 'Oils & ghee': 'तेल और घी', 'Dairy & bakery': 'डेयरी और बेकरी', 'Fruits & veg': 'फल-सब्ज़ी', 'Snacks & sweets': 'नमकीन-मिठाई', 'Beverages': 'पेय', 'Household': 'घरेलू', 'Festive & pooja': 'त्योहार और पूजा' };
const catName = (c) => (lang === 'hi' ? CAT_HI[c] || c : c);

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}
function toast(msg) {
  const el = $('toast'); el.textContent = msg; el.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => (el.hidden = true), 3200);
}

// ---------- research on an item, using the stock as it is now ----------
const recFor = (id) => state.research?.recs.find((p) => p.id === id);
function advice(item) {
  const p = recFor(item.id);
  if (!p) return null;
  if (p.stock === 'stock_up' || p.stock === 'restock') {
    const need = Math.max(0, (p.stock === 'stock_up' ? p.target : item.reorder) - item.qty);
    if (!need) return { p, cls: 'done', label: t('done'), need: 0 };
    return { p, cls: p.stock, label: p.stock === 'stock_up' ? t('up', need) : t('re', need), need };
  }
  if (p.stock === 'slow') return { p, cls: 'slow', label: t('slow'), need: 0 };
  if (!p.researched) return null;  // only the focus items were searched
  return { p, cls: 'ok', label: t('ok'), need: 0 };
}
function needsAction(item) {
  const a = advice(item);
  return a ? a.need > 0 || a.cls === 'slow' : item.qty <= 0.5 * item.reorder;
}
function spark(values) {
  if (!values || values.length < 2) return '';
  const max = Math.max(...values, 1), w = 200, h = 26;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - 2 - (v / max) * (h - 4)}`).join(' ');
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="#f2a93b" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
}

// ---------- render ----------
function renderTop() {
  const s = state.summary, items = state.items;
  $('k-items').textContent = items.length;
  $('k-cats').textContent = t('cats', new Set(items.map((i) => i.category)).size);
  $('k-value').textContent = rupees(items.reduce((a, i) => a + i.qty * i.cost, 0));
  const low = items.filter((i) => i.qty <= 0.5 * i.reorder);
  $('k-low').textContent = low.length;
  $('k-low-names').textContent = low.length ? low.slice(0, 4).map((i) => (lang === 'hi' && i.hindi) || i.name).join(', ') : t('none_low');
  $('k-fest-label').textContent = t('diwali');
  $('k-fest').textContent = t('days', state.diwali);
  $('k-fest-sub').textContent = t('fest_sub', lang === 'hi' ? state.festival.hi : state.festival.name, state.festival.days);

  const r = state.research;
  $('plan-empty').hidden = !!r; $('plan-full').hidden = !r;
  if (!r) return;
  let up = 0, re = 0, slow = 0, units = 0, spend = 0;
  for (const i of items) {
    const a = advice(i);
    if (!a) continue;
    if (a.cls === 'stock_up') up++; else if (a.cls === 'restock') re++; else if (a.cls === 'slow') slow++;
    units += a.need; spend += a.need * i.cost;
  }
  $('t-up').textContent = t('t_up', up); $('t-re').textContent = t('t_re', re); $('t-slow').textContent = t('t_slow', slow);
  $('t-order').innerHTML = units ? t('t_order', units, rupees(spend)) : t('t_none');
  $('apply').disabled = !units;
  const n = (r.budget?.live || 0) + (r.budget?.cached || 0);
  $('t-when').textContent = t('t_when', new Date(r.date).toLocaleDateString(lang === 'hi' ? 'hi-IN' : 'en-IN', { day: 'numeric', month: 'short' }), n);
}

function renderCats() {
  const counts = {};
  for (const i of state.items) counts[i.category] = (counts[i.category] || 0) + 1;
  $('cats').innerHTML = ['All', ...state.summary.categories.filter((c) => counts[c])].map((c) =>
    `<button type="button" data-cat="${esc(c)}" aria-pressed="${c === cat}">${c === 'All' ? t('all') : esc(catName(c))}<span>${c === 'All' ? state.items.length : counts[c]}</span></button>`).join('');
}

function card(i) {
  const a = advice(i);
  const name = lang === 'hi' && i.hindi ? i.hindi : i.name, sub = lang === 'hi' ? i.name : i.hindi;
  const pct = Math.min(100, Math.round((i.qty / Math.max(i.reorder, 1)) * 100));
  const why = a ? (a.cls === 'done' ? '' : lang === 'hi' ? a.p.action_hi : a.p.action_en) : '';
  return `<article class="item" data-id="${i.id}">
    <div class="pic">${i.image ? `<img src="${esc(i.image)}" alt="" loading="lazy">` : `<div class="ph">${esc(i.name[0])}</div>`}
      ${a ? `<span class="badge ${a.cls}">${esc(a.label)}</span>` : ''}
      <div class="tools"><button type="button" data-edit="${i.id}" aria-label="Edit ${esc(i.name)}">✎</button><button type="button" data-del="${i.id}" aria-label="Remove ${esc(i.name)}">🗑</button></div>
    </div>
    <div class="info">
      <h3>${esc(name)}${sub ? `<small>${esc(sub)}</small>` : ''}</h3>
      <div class="qty">
        <button type="button" data-step="-1" aria-label="One less">−</button>
        <input type="number" min="0" value="${i.qty}" data-qty="${i.id}" aria-label="${esc(i.name)} in stock">
        <button type="button" data-step="1" aria-label="One more">+</button>
        <span class="of">${t('normal', i.reorder, i.unit)}</span>
      </div>
      <div class="bar-level"><i class="${i.qty <= 0.5 * i.reorder ? 'low' : ''}" style="width:${pct}%"></i></div>
      ${a && a.p.spark?.length ? spark(a.p.spark) : ''}
      ${why ? `<p class="why">${esc(why)}</p>` : ''}
      <div class="meta"><span>${rupees(i.price)}</span><span>${esc(catName(i.category))}</span></div>
    </div>
  </article>`;
}

function renderGrid() {
  const q = $('q').value.trim().toLowerCase();
  const rows = state.items.filter((i) => (cat === 'All' || i.category === cat) && (!onlyAction || needsAction(i)) &&
    (!q || `${i.name} ${i.hindi} ${i.term}`.toLowerCase().includes(q)));
  if (onlyAction) rows.sort((x, y) => (advice(y)?.need || 0) - (advice(x)?.need || 0));
  $('grid').innerHTML = rows.map(card).join('') || `<p class="empty">${t('empty')}</p>`;
}
function render() { renderTop(); renderCats(); renderGrid(); }

async function load(flashIds = []) {
  const d = await api('/api/store');
  state = { ...state, ...d, summary: d.summary };
  render();
  for (const id of flashIds) {
    const el = document.querySelector(`.item[data-id="${id}"]`);
    if (el) { el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 2600); }
  }
  if (flashIds.length) document.querySelector(`.item[data-id="${flashIds[0]}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ---------- stock editing ----------
async function setQty(id, qty) {
  const item = state.items.find((i) => i.id === id);
  if (!item || qty < 0) return;
  item.qty = qty;
  renderTop(); renderGrid();
  await api(`/api/items/${id}`, { method: 'PATCH', body: { qty } });
}
$('grid').addEventListener('click', async (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  const id = Number(b.closest('.item').dataset.id), item = state.items.find((i) => i.id === id);
  if (b.dataset.step) await setQty(id, item.qty + Number(b.dataset.step));
  else if (b.dataset.edit) openDialog(item);
  else if (b.dataset.del && confirm(t('del', item.name))) { await api(`/api/items/${id}`, { method: 'DELETE' }); await load(); }
});
$('grid').addEventListener('change', (e) => { if (e.target.dataset.qty) setQty(Number(e.target.dataset.qty), Math.max(0, parseInt(e.target.value || '0', 10))); });
$('cats').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { cat = b.dataset.cat; renderCats(); renderGrid(); } });
$('q').addEventListener('input', renderGrid);
for (const [id, v] of [['f-all', false], ['f-act', true]]) $(id).onclick = () => {
  onlyAction = v; $('f-all').setAttribute('aria-pressed', String(!v)); $('f-act').setAttribute('aria-pressed', String(v)); renderGrid();
};
$('reset').onclick = async () => { if (confirm(t('reset_q'))) { await api('/api/store/reset', { method: 'POST' }); await load(); } };
$('apply').onclick = async () => {
  const r = await api('/api/orders/apply', { method: 'POST', body: {} });
  toast(r.done.length ? t('applied', r.done.length) : t('nothing'));
  await load(r.actions.map((a) => a.id));
};

let editing = null;
function openDialog(item = null) {
  editing = item;
  const f = $('item-form');
  f.category.innerHTML = state.summary.categories.map((c) => `<option value="${esc(c)}">${esc(catName(c))}</option>`).join('');
  $('dlg-title').textContent = item ? t('edit_title') : t('add_title');
  for (const k of ['name', 'hindi', 'category', 'unit', 'qty', 'reorder', 'cost', 'price', 'term']) f[k].value = item ? item[k] ?? '' : '';
  if (!item) { f.category.value = cat !== 'All' ? cat : 'Staples'; f.qty.value = 0; }
  $('dlg').showModal();
}
$('add').onclick = () => openDialog();
$('dlg').addEventListener('close', async () => {
  if ($('dlg').returnValue !== 'save') return;
  const f = $('item-form'), body = {};
  for (const k of ['name', 'hindi', 'category', 'unit', 'term']) body[k] = f[k].value.trim();
  for (const k of ['qty', 'reorder', 'cost', 'price']) if (f[k].value !== '') body[k] = Number(f[k].value);
  try {
    const saved = editing ? await api(`/api/items/${editing.id}`, { method: 'PATCH', body }) : await api('/api/items', { method: 'POST', body });
    await load([saved.id]);
  } catch (err) { toast(err.message); }
});

// ---------- research overlay (the 3D Research Room) ----------
function openResearch() {
  $('overlay').hidden = false;
  $('close').textContent = t('close_busy'); $('close').classList.add('wait');
  $('room').src = `/room?autostart=1&lang=${lang}`;
  document.body.style.overflow = 'hidden';
}
function closeResearch() {
  $('overlay').hidden = true; $('room').src = 'about:blank';
  fetch('/api/research/pause', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paused: false }) }).catch(() => {});
  document.body.style.overflow = '';
  load();
}
$('research').onclick = openResearch;
$('replay').onclick = openResearch;
$('close').onclick = closeResearch;
addEventListener('message', async (e) => {
  if (e.origin !== location.origin || e.data?.type !== 'research-done') return;
  $('close').textContent = t('close_done'); $('close').classList.remove('wait');
  await load();
  toast(t('ready'));
});
addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('overlay').hidden) closeResearch(); });

// ---------- stock agent ----------
function md(s) {
  const lines = esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').split('\n');
  let html = '', list = false;
  for (const l of lines) {
    const m = l.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)/);
    if (m) { if (!list) { html += '<ul>'; list = true; } html += `<li>${m[1]}</li>`; continue; }
    if (list) { html += '</ul>'; list = false; }
    if (l.trim()) html += `<p>${l}</p>`;
  }
  return html + (list ? '</ul>' : '');
}
function bubble(cls, html) {
  const li = document.createElement('li'); li.className = cls; li.innerHTML = html;
  $('chat').appendChild(li); $('chat').scrollTop = $('chat').scrollHeight; return li;
}
function traceHtml(r) {
  const spans = (r.actions || []).map((a) => a.kind === 'update' ? `<span class="ch">${esc(a.name)} ${a.qty_before} → ${a.qty}</span>`
    : `<span class="ch">${a.kind} ${esc(a.name)}</span>`);
  for (const tr of r.trace || []) if (!['change_stock', 'add_item', 'remove_item', 'apply_reorders'].includes(tr.tool))
    spans.push(`<span>${esc(tr.tool)}${tr.args?.q ? ' · ' + esc(tr.args.q) : tr.args?.name ? ' · ' + esc(tr.args.name) : ''}</span>`);
  return spans.length ? `<div class="trace">${spans.join('')}</div>` : '';
}
async function send(text) {
  if (!text.trim()) return;
  chat.push({ role: 'user', content: text });
  bubble('me', esc(text));
  $('msg').value = ''; $('msg').disabled = true;
  const wait = bubble('bot think', t('thinking'));
  try {
    const r = await api('/api/agent', { method: 'POST', body: { messages: chat } });
    wait.className = 'bot'; wait.innerHTML = md(r.reply) + traceHtml(r);
    chat.push({ role: 'assistant', content: r.reply });
    if (r.actions?.length) await load(r.actions.filter((a) => a.kind !== 'remove').map((a) => a.id));
  } catch (err) { wait.className = 'bot'; wait.textContent = err.message; }
  $('msg').disabled = false; $('msg').focus();
}
$('ask').addEventListener('submit', (e) => { e.preventDefault(); send($('msg').value); });
$('suggest').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b && !$('msg').disabled) send(b.textContent); });

// ---------- language ----------
function applyLang() {
  document.documentElement.lang = lang;
  for (const el of document.querySelectorAll('[data-t]')) { const v = T[lang][el.dataset.t]; if (typeof v === 'string') el.textContent = v; }
  $('q').placeholder = t('search'); $('msg').placeholder = t('msg');
  if (!chat.length) $('chat').innerHTML = `<li class="bot">${esc(t('hello'))}</li>`;
  $('suggest').innerHTML = T[lang].suggest.map((s) => `<button type="button">${esc(s)}</button>`).join('');
  if (state.summary) render();
}

applyLang();
load();
