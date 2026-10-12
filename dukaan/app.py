"""Dukaan Radar web app: one supermarket in Dadar, Mumbai.   uv run uvicorn dukaan.app:app --port 8790

/            the store: map, stock, research results, stock agent
/room        the Research Room (3D), shown while research runs
/api/...     stock CRUD, research (server-sent events), agent chat
"""
import json
import os
import queue
import threading
from datetime import date
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import agent, inventory, research, serp
from .config import ANCHOR, FESTIVALS, next_festival
from .store_seed import STORE

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LAST = inventory.DATA / "last_research.json"
DEMO_DAY = json.loads((ROOT / "demo" / "demo.json").read_text())["day"] if serp.DEMO and (ROOT / "demo" / "demo.json").exists() else None

app = FastAPI(title="Dukaan Radar")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


def _today():
    return date.fromisoformat(DEMO_DAY) if DEMO_DAY else date.today()


def _load_last():
    if not agent.LAST_RESEARCH and LAST.exists():
        agent.LAST_RESEARCH.update(json.loads(LAST.read_text(encoding="utf-8")))
    return agent.LAST_RESEARCH


@app.get("/", response_class=HTMLResponse)
def store_page(request: Request, lang: str = "en"):
    return templates.TemplateResponse(request, "store.html", dict(
        request=request, store=STORE, lang="hi" if lang == "hi" else "en", demo=serp.DEMO,
        agent_ready=bool(os.environ.get("TOKENROUTER_API_KEY"))))


@app.get("/room", response_class=HTMLResponse)
def room(request: Request, lang: str = "en"):
    return templates.TemplateResponse(request, "room.html", dict(request=request, store=STORE, lang="hi" if lang == "hi" else "en", demo=serp.DEMO))


# ---------- stock ----------
@app.get("/api/store")
def api_store():
    today = _today()
    when, name, hi = next_festival(today) or FESTIVALS[ANCHOR]
    return dict(summary=inventory.summary(), items=inventory.items(), research=_load_last() or None,
                today=today.isoformat(), festival=dict(name=name, hi=hi, date=when.isoformat(), days=(when - today).days),
                diwali=(FESTIVALS[ANCHOR][0] - today).days)


@app.post("/api/orders/apply")
def api_apply(body: dict = Body(default={})):
    _load_last()
    actions = []
    done = agent.apply_orders(body.get("names"), actions)
    return dict(done=done, actions=actions)


@app.post("/api/items")
def api_add(item: dict = Body(...)):
    try:
        return inventory.add(item.get("name", ""), item.get("category", "Staples"), item.get("unit", "unit"),
                             int(item.get("qty") or 0), item.get("reorder"), item.get("cost") or 0,
                             item.get("price") or 0, item.get("term"), item.get("hindi") or "")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/items/{item_id}")
def api_update(item_id: int, changes: dict = Body(...)):
    if not inventory.find(item_id):
        raise HTTPException(404, "no such item")
    return inventory.update(item_id, **changes)


@app.delete("/api/items/{item_id}")
def api_delete(item_id: int):
    inventory.remove(item_id)
    return {"ok": True}


@app.post("/api/store/reset")
def api_reset():
    inventory.reset()
    return {"ok": True}


# ---------- research ----------
@app.get("/api/research")
def api_research():
    """Server-sent events: each search as a worker starts and finishes it, then the full report."""
    if not research.RUNNING.acquire(blocking=False):
        busy = dict(type="error", message="A research run is already going on. Wait for it to finish.")
        return StreamingResponse(iter(["data: " + json.dumps(busy) + "\n\n"]), media_type="text/event-stream")
    research.GO.set()
    events = queue.Queue()

    def work():
        try:
            r = research.build(today=_today(), listener=events.put)
            agent.LAST_RESEARCH.clear()
            agent.LAST_RESEARCH.update(r)
            LAST.parent.mkdir(parents=True, exist_ok=True)
            LAST.write_text(json.dumps(r, ensure_ascii=False, default=str), encoding="utf-8")
            events.put(dict(type="report", report=r))
        except Exception as e:
            events.put(dict(type="error", message=str(e)))
        finally:
            research.GO.set()
            research.RUNNING.release()
        events.put(None)

    threading.Thread(target=work, daemon=True).start()

    def stream():
        try:
            while (ev := events.get()) is not None:
                yield "data: " + json.dumps(ev, ensure_ascii=False, default=str) + "\n\n"
        finally:
            research.GO.set()  # the viewer left: never stay paused

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/research/pause")
def api_pause(body: dict = Body(default={})):
    research.GO.clear() if body.get("paused", True) else research.GO.set()
    return dict(paused=not research.GO.is_set())


# ---------- agent ----------
AGENT_USE = {}
@app.post("/api/agent")
def api_agent(body: dict = Body(...)):
    if not os.environ.get("TOKENROUTER_API_KEY"):
        return dict(reply="The stock agent needs TOKENROUTER_API_KEY in .env (any OpenAI-compatible model works).", actions=[], trace=[])
    limit = int(os.environ.get("AGENT_DAILY_LIMIT") or 0)  # set on public deployments to cap model spend
    if limit:
        day = date.today().isoformat()
        if AGENT_USE.get("day") != day:
            AGENT_USE.update(day=day, n=0)
        if AGENT_USE["n"] >= limit:
            return dict(reply="The demo agent has reached today's message limit. Please try again tomorrow.", actions=[], trace=[])
        AGENT_USE["n"] += 1
    _load_last()
    try:
        return agent.chat(body.get("messages", []))
    except Exception as e:
        return dict(reply=f"Sorry, the agent hit an error: {e}", actions=[], trace=[])


@app.get("/api/budget")
def api_budget():
    try:
        return serp.account()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)
