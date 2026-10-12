"""The stock agent: a chat assistant that can read and change the shop's inventory, read the latest
demand research, and look up live prices and news.

Brain: any OpenAI-compatible model via TokenRouter (TOKENROUTER_API_KEY / _BASE_URL / _MODEL_STRONG).
Live lookups: SerpApi's own serpapi-search-tools package (shopping_search, news_search), given our
cached client so every search is cached, counted and stored without the API key.
"""
import json
import os

from . import inventory, serp
from .store_seed import STORE

MAX_STEPS = 6
LAST_RESEARCH = {}  # set by the app after each research run


class CachedClient:
    """serpapi-search-tools SearchClient that goes through Dukaan Radar's cache."""

    def __init__(self, tally=None):
        self.tally = tally

    def search(self, params):
        params = {k: v for k, v in params.items() if k != "output"}  # ask for JSON (cacheable); the package formats it
        return serp.search(params, ttl_hours=12, tally=self.tally)


def _search_tools(tally):
    from serpapi_search_tools import news_search, shopping_search
    client = CachedClient(tally)
    shop = shopping_search(provider="function", client=client, result_limit=8, response_format="json",
                           default_params={"location": STORE["location"], "gl": "in", "hl": "en"})
    news = news_search(provider="function", client=client, result_limit=6, response_format="json", default_params={"gl": "in", "hl": "en"})
    return shop, news


def _brief(r):
    return dict(id=r["id"], name=r["name"], category=r["category"], unit=r["unit"], qty=r["qty"], normal=r["reorder"],
                cost=r["cost"], price=r["price"])


def _rec_brief(p):
    return dict(name=p["name"], advice=p["stock_en"], order=p["order"], qty=p["qty"], normal=p["reorder"],
                demand_factor=p["demand"], why=p["action_en"])


TOOLS = [
    ("list_inventory", "List items in stock, optionally only one category or only items at half their normal stock or below.",
     {"category": {"type": "string", "description": "Optional category name"}, "low_only": {"type": "boolean"}}, []),
    ("get_item", "Details of one item by name.", {"name": {"type": "string"}}, ["name"]),
    ("change_stock", "Change an item's quantity: give `add` (positive or negative units) or `set_qty`. Optionally a new selling `price`.",
     {"name": {"type": "string"}, "add": {"type": "integer"}, "set_qty": {"type": "integer"}, "price": {"type": "number"}}, ["name"]),
    ("add_item", "Add a new product to the shop.",
     {"name": {"type": "string"}, "category": {"type": "string", "enum": inventory.CATEGORIES}, "unit": {"type": "string"},
      "qty": {"type": "integer"}, "cost": {"type": "number"}, "price": {"type": "number"},
      "search_term": {"type": "string", "description": "What people type into Google for it"}}, ["name", "category", "unit", "qty"]),
    ("remove_item", "Remove a product from the shop entirely.", {"name": {"type": "string"}}, ["name"]),
    ("latest_research", "The latest demand research: what to stock up, restock or slow down, with reasons.",
     {"advice": {"type": "string", "enum": ["all", "stock_up", "restock", "slow"]}}, []),
    ("apply_reorders", "Receive the recommended order quantities into stock (what the research said to order).",
     {"names": {"type": "array", "items": {"type": "string"}, "description": "Only these items; omit for all"}}, []),
    ("shopping_prices", "Live Google Shopping results in Mumbai for a product (prices, sellers).", {"q": {"type": "string"}}, ["q"]),
    ("news", "Live Google News headlines, e.g. price rises or shortages.", {"q": {"type": "string"}}, ["q"]),
]
TOOL_SPECS = [{"type": "function", "function": {"name": n, "description": d,
                                                "parameters": {"type": "object", "properties": p, "required": req}}}
              for n, d, p, req in TOOLS]

SYSTEM = f"""You are the stock manager of {STORE['name']}, a supermarket in {STORE['area']}.
You help the owner keep the right stock. Use the tools: never invent quantities, prices or demand figures.
When the owner asks you to change stock, do it with a tool, then confirm in one short sentence what changed.
Demand advice comes from the latest research (live Google search data via SerpApi); say so when you use it.
Answer in the owner's language (Hindi or English), briefly, like a helpful shop assistant. Prices are in rupees."""


def still_needed(p, row):
    """Units still to order for a research recommendation, given the stock as it is now."""
    if not row or p["stock"] not in ("stock_up", "restock"):
        return 0
    goal = p["target"] if p["stock"] == "stock_up" else row["reorder"]
    return max(0, goal - row["qty"])


def apply_orders(names=None, actions=None):
    """Receive the research's recommended orders into stock (only what is still missing)."""
    wanted = {n.lower() for n in names} if names else None
    done = []
    for p in LAST_RESEARCH.get("recs", []):
        row = inventory.find(p["id"])
        if wanted and not (row and (row["name"].lower() in wanted or row["term"] in wanted)):
            continue
        need = still_needed(p, row)
        if need:
            new = inventory.update(row["id"], qty=row["qty"] + need)
            if actions is not None:
                actions.append(dict(kind="update", id=new["id"], name=new["name"], qty_before=row["qty"], qty=new["qty"]))
            done.append(f"{new['name']} +{need}")
    return done


def _run_tool(name, args, tally, actions):
    if name == "list_inventory":
        rows = inventory.items()
        if args.get("category"):
            rows = [r for r in rows if r["category"].lower() == args["category"].lower()]
        if args.get("low_only"):
            rows = [r for r in rows if inventory.is_low(r)]
        return [_brief(r) for r in rows]
    if name == "get_item":
        r = inventory.find(args["name"])
        return _brief(r) if r else f"No item called {args['name']}"
    if name == "change_stock":
        r = inventory.find(args["name"])
        if not r:
            return f"No item called {args['name']}"
        qty = args["set_qty"] if args.get("set_qty") is not None else r["qty"] + int(args.get("add") or 0)
        new = inventory.update(r["id"], qty=qty, price=args.get("price"))
        actions.append(dict(kind="update", id=new["id"], name=new["name"], qty_before=r["qty"], qty=new["qty"]))
        return _brief(new)
    if name == "add_item":
        new = inventory.add(args["name"], args["category"], args["unit"], args["qty"], cost=args.get("cost") or 0,
                            price=args.get("price") or 0, term=args.get("search_term"))
        actions.append(dict(kind="add", id=new["id"], name=new["name"], qty=new["qty"]))
        return _brief(new)
    if name == "remove_item":
        r = inventory.find(args["name"])
        if not r:
            return f"No item called {args['name']}"
        inventory.remove(r["id"])
        actions.append(dict(kind="remove", id=r["id"], name=r["name"]))
        return f"Removed {r['name']}"
    if name == "latest_research":
        recs = LAST_RESEARCH.get("recs")
        if not recs:
            return "No research has been run yet. Ask the owner to press Run research."
        want = args.get("advice", "all")
        return dict(date=LAST_RESEARCH.get("date"), totals=LAST_RESEARCH.get("totals"),
                    items=[_rec_brief(p) for p in recs if want == "all" and p["stock"] != "ok" or p["stock"] == want])
    if name == "apply_reorders":
        return apply_orders(args.get("names"), actions) or "Nothing left to order."
    if name in ("shopping_prices", "news"):
        shop, news = _search_tools(tally)
        out = (shop if name == "shopping_prices" else news)(query=args["q"])
        data = json.loads(out) if isinstance(out, str) else out
        if name == "shopping_prices":  # keep what a shopkeeper needs, not the full listing JSON
            return [dict(title=x.get("title"), price=x.get("price"), seller=x.get("source"), rating=x.get("rating"))
                    for x in data.get("shopping_results", [])[:8]]
        return [dict(title=x.get("title"), source=(x.get("source") or {}).get("name"), date=x.get("date"))
                for x in data.get("news_results", [])[:6]]
    return f"Unknown tool {name}"


def chat(messages, listener=None):
    """messages: [{role, content}] from the page. Returns the reply, the stock changes made and the searches used."""
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["TOKENROUTER_API_KEY"], base_url=os.environ.get("TOKENROUTER_BASE_URL", "https://api.tokenrouter.com/v1"))
    model = os.environ.get("TOKENROUTER_MODEL_STRONG", "anthropic/claude-sonnet-5.5")
    tally = serp.Tally(listener)
    actions, trace = [], []
    convo = [{"role": "system", "content": SYSTEM}] + [m for m in messages if m.get("role") in ("user", "assistant")][-12:]
    for _ in range(MAX_STEPS):
        r = client.chat.completions.create(model=model, messages=convo, tools=TOOL_SPECS, max_tokens=700)
        msg = r.choices[0].message
        if not msg.tool_calls:
            return dict(reply=msg.content or "", actions=actions, trace=trace, searches=tally.as_dict())
        convo.append({"role": "assistant", "content": msg.content or None, "tool_calls": [  # empty text is rejected
            {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in msg.tool_calls]})
        for c in msg.tool_calls:
            try:
                args = json.loads(c.function.arguments or "{}")
                result = _run_tool(c.function.name, args, tally, actions)
            except Exception as e:
                args, result = {}, f"Error: {e}"
            trace.append(dict(tool=c.function.name, args=args))
            convo.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(result, ensure_ascii=False, default=str)[:6000]})
    return dict(reply="I made several changes; please check the stock list.", actions=actions, trace=trace, searches=tally.as_dict())
