"""The bundled demo data replayed: no API key, no live searches, a fresh store in a temp folder."""
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(code, tmp_path=None):
    env = {**os.environ, "DUKAAN_DEMO": "1", "SERPAPI_API_KEY": "", "TOKENROUTER_API_KEY": "", "PYTHONIOENCODING": "utf-8"}
    if tmp_path:
        env["DUKAAN_DATA"] = str(tmp_path)
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)


def test_demo_reports_build_without_live_searches():
    out = run("""
from datetime import date
from dukaan import report
for city, shop in [('pune','gifts'),('ahmedabad','apparel'),('patna','gifts'),('delhi','electronics')]:
    r = report.build(city, shop, today=date(2026,10,11))
    assert r['budget']['live'] == 0 and not r['errors'], (city, r['errors'])
    assert len(r['picks']) == 4 and all(p['action_en'] and p['action_hi'] for p in r['picks'])
    assert r['states'] and r['picks'][0]['price']
r = report.build('pune','gifts', today=date(2026,10,11))
assert {p['term'] for p in r['picks']} == {'rangoli','akash kandil','dandiya','gift hamper'}
assert [p['action'] for p in r['picks'] if p['term']=='dandiya'] == ['last_call']
print('ok')
""")
    assert out.returncode == 0, out.stderr[-2000:]


def test_store_pages_and_stock_editing(tmp_path):
    out = run("""
from fastapi.testclient import TestClient
from dukaan.app import app
c = TestClient(app)
assert 'Dukaan Radar Mart' in c.get('/').text and 'Demo mode' in c.get('/').text
assert c.get('/?lang=hi').status_code == 200 and 'Research Room' in c.get('/room').text
s = c.get('/api/store').json()
assert len(s['items']) == 50 and s['research'] is None and s['diwali'] == 27
new = c.post('/api/items', json={'name': 'Kesar', 'category': 'Festive & pooja', 'unit': '1 g', 'qty': 4}).json()
assert c.post('/api/items', json={'name': 'kesar', 'category': 'Staples', 'qty': 1}).status_code == 400
assert c.patch(f"/api/items/{new['id']}", json={'qty': 9, 'price': 250}).json()['qty'] == 9
assert c.patch(f"/api/items/{new['id']}", json={'qty': -3}).json()['qty'] == 0
c.delete(f"/api/items/{new['id']}")
assert len(c.get('/api/store').json()['items']) == 50
assert 'TOKENROUTER_API_KEY' in c.post('/api/agent', json={'messages': [{'role': 'user', 'content': 'hi'}]}).json()['reply']
print('ok')
""", tmp_path)
    assert out.returncode == 0, out.stderr[-2000:]


def test_no_api_key_in_shipped_files():
    key_file = ROOT / ".env"
    key = next((l.split("=", 1)[1].strip() for l in key_file.read_text().splitlines() if l.startswith("SERPAPI_API_KEY=")), "") if key_file.exists() else ""
    if not key:
        return
    tracked = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    leaks = [f for f in tracked if key.encode() in (ROOT / f).read_bytes()]
    assert not leaks, f"API key found in {leaks}"


def test_store_research_stream_and_orders(tmp_path):
    out = run("""
import json
from fastapi.testclient import TestClient
from dukaan.app import app
c = TestClient(app)
events = [json.loads(l[6:]) for l in c.get('/api/research').text.splitlines() if l.startswith('data: ')]
done = [e for e in events if e['type'] == 'search' and e['phase'] == 'done']
assert len(done) == 10 and all(e['source'] == 'cache' for e in done)
assert {e['worker'] for e in done} == {'scout', 'historian', 'price', 'news'}
r = events[-1]['report']
assert events[-1]['type'] == 'report' and not r['errors'] and len(r['recs']) == 50
assert r['totals']['stock_up'] >= 3 and r['totals']['restock'] >= 3 and len(r['competitors']) >= 5
assert {p['stock'] for p in r['recs'] if p['category'] == 'Staples' and p['name'] == 'Salt'} <= {'ok', 'slow'}
assert all(p['action_en'] and p['action_hi'] for p in r['recs']) and sum(p['researched'] for p in r['recs']) == 6
assert c.get('/api/store').json()['research']['date'] == '2026-10-12'
applied = c.post('/api/orders/apply', json={}).json()
assert len(applied['done']) == r['totals']['stock_up'] + r['totals']['restock']
assert c.post('/api/orders/apply', json={}).json()['done'] == []   # a second press orders nothing more
print('ok')
""", tmp_path)
    assert out.returncode == 0, out.stderr[-2000:]
