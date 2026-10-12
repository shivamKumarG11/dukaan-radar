"""Dukaan Radar web app.   uv run uvicorn dukaan.app:app --reload   -> http://127.0.0.1:8000"""
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Query, Request
import json
import queue
import threading

from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import report, serp
from .config import CITIES, SHOP_TYPES

HERE = Path(__file__).resolve().parent
DEMO_DAY = None
if serp.DEMO and (HERE.parent / "demo" / "demo.json").exists():
    import json
    DEMO_DAY = json.loads((HERE.parent / "demo" / "demo.json").read_text())["day"]  # replay as of the recording day


def _today(day):
    return date.fromisoformat(day or DEMO_DAY) if (day or DEMO_DAY) else date.today()


app = FastAPI(title="Dukaan Radar")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


def spark_paths(values, w=280, h=60):
    """SVG line and area paths for a sparkline (values 0-100)."""
    if not values:
        return "", ""
    top = max(max(values), 1)
    step = w / max(len(values) - 1, 1)
    pts = [(round(i * step, 1), round(h - 4 - (v / top) * (h - 8), 1)) for i, v in enumerate(values)]
    line = "M" + " L".join(f"{x},{y}" for x, y in pts)
    return line, f"{line} L{w},{h} L0,{h} Z"


templates.env.globals.update(spark_paths=spark_paths)


def _report(city, shop, today):
    if city not in CITIES:
        city = "pune"
    if shop not in SHOP_TYPES:
        shop = "gifts"
    return report.build(city, shop, today=today)


def _ctx(request, city, shop, lang, today):
    return dict(request=request, r=_report(city, shop, today), lang=lang if lang in ("en", "hi") else "en",
                cities=CITIES, shops=SHOP_TYPES, demo=serp.DEMO)


@app.get("/", response_class=HTMLResponse)
def room(request: Request, city: str = "pune", shop: str = "gifts", lang: str = "en"):
    """The Research Room: watch the workers research, then take the plan."""
    return templates.TemplateResponse(request, "room.html", dict(
        request=request, city=city if city in CITIES else "pune", shop=shop if shop in SHOP_TYPES else "gifts",
        lang=lang if lang in ("en", "hi") else "en", cities=CITIES, shops=SHOP_TYPES, demo=serp.DEMO))


@app.get("/api/run")
def api_run(city: str = "pune", shop: str = "gifts", day: str | None = None):
    """Server-sent events: every search as a worker starts and finishes it, then the full report."""
    city = city if city in CITIES else "pune"
    shop = shop if shop in SHOP_TYPES else "gifts"
    events = queue.Queue()

    def work():
        try:
            r = report.build(city, shop, today=_today(day), listener=events.put)
            events.put(dict(type="report", report=r))
        except Exception as e:  # surfaced to the page
            events.put(dict(type="error", message=str(e)))
        events.put(None)

    threading.Thread(target=work, daemon=True).start()

    def stream():
        while (ev := events.get()) is not None:
            yield "data: " + json.dumps(ev, ensure_ascii=False, default=str) + "\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/classic", response_class=HTMLResponse)
def dashboard(request: Request, city: str = "pune", shop: str = "gifts", lang: str = "en", day: str | None = None):
    today = _today(day)
    return templates.TemplateResponse(request, "dashboard.html", _ctx(request, city, shop, lang, today))


@app.get("/brief", response_class=HTMLResponse)
def brief(request: Request, city: str = "pune", shop: str = "gifts", lang: str = "hi", day: str | None = None):
    today = _today(day)
    return templates.TemplateResponse(request, "brief.html", _ctx(request, city, shop, lang, today))


@app.get("/api/report")
def api_report(city: str = "pune", shop: str = "gifts", day: str | None = None):
    today = _today(day)
    return JSONResponse(_report(city, shop, today))


@app.get("/api/budget")
def api_budget():
    try:
        return serp.account()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)
