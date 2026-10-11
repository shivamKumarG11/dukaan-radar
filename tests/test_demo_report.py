"""Full reports rebuilt from the bundled demo data: no API key, no live searches."""
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(code):
    env = {**os.environ, "DUKAAN_DEMO": "1", "SERPAPI_API_KEY": "", "PYTHONIOENCODING": "utf-8"}
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


def test_web_pages_render_in_demo_mode():
    out = run("""
from fastapi.testclient import TestClient
from dukaan.app import app
c = TestClient(app)
for path in ['/?city=pune&shop=gifts', '/?city=pune&shop=gifts&lang=hi', '/brief?city=delhi&shop=electronics', '/api/report?city=patna&shop=gifts']:
    r = c.get(path); assert r.status_code == 200, path
assert 'Demo mode' in c.get('/').text and 'आज का स्टॉक प्लान' in c.get('/brief').text
print('ok')
""")
    assert out.returncode == 0, out.stderr[-2000:]


def test_no_api_key_in_shipped_files():
    key_file = ROOT / ".env"
    key = next((l.split("=", 1)[1].strip() for l in key_file.read_text().splitlines() if l.startswith("SERPAPI_API_KEY=")), "") if key_file.exists() else ""
    if not key:
        return
    tracked = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    leaks = [f for f in tracked if key.encode() in (ROOT / f).read_bytes()]
    assert not leaks, f"API key found in {leaks}"
