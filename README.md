# Dukaan Radar

**A stock radar for one supermarket in Dadar, Mumbai.** The store keeps 50 items. Press *Run demand research*, and four 3D workers check every item against live Google search data via SerpApi: Trends for Maharashtra, last season's Diwali curve, Shopping prices in Mumbai, News, and Maps for nearby supermarkets. Every item then gets a call: **Stock up +N**, **Restock +N**, **Slow down** or **OK**, with the reason in English and Hindi. A stock agent, an LLM with tools, changes the stock when you tell it what came in, answers "what should I order for Diwali?" from the research, and looks up live prices and news.

Built for the SerpApi India Hackathon 2026.

## What it does

- **Store page:** shows the store on Google Maps, plus KPIs (stock value, items running low, days to Diwali). It also has the stock grid: product photos, quantity −/+, add, edit and remove.
- **Research:** a run takes 28 SerpApi searches the first time and is cached afterwards. It opens the 3D Research Room, where each speech bubble is a real search, and Munshi writes the plan on the chalkboard. Back in the store, every card shows its call and its evidence (a Trends sparkline and the reason).
- **Apply all orders:** receives the recommended quantities into stock. It works from the stock as it is now, so a second press orders nothing more.
- **Stock agent** (TokenRouter, any OpenAI-compatible model). Its tools:
  - list, get and change stock; add or remove items
  - read the latest research and apply its orders
  - live **Google Shopping** and **Google News** through SerpApi's own `serpapi-search-tools` package, routed through our cache

  Cards it changes flash on the page.

On 12 Oct 2026 (Navratri, 27 days to Diwali) the research said:
- stock up 22 items, led by chakli, rangoli colours, soan papdi and kaju katli
- restock ghee, paneer, eggs, akash kandil and gift hampers
- about 327 units for ₹48k at cost

Salt and water stay **OK** even when their searches move: demand factors are capped per category.

## Run it

```bash
uv sync
uv run uvicorn dukaan.app:app --port 8790      # http://127.0.0.1:8790
```

`.env`:
```
SERPAPI_API_KEY=...            # live research (without it, the bundled demo recording is replayed)
TOKENROUTER_API_KEY=...        # the stock agent's brain
TOKENROUTER_BASE_URL=https://api.tokenrouter.com/v1
TOKENROUTER_MODEL_STRONG=anthropic/claude-sonnet-5.5
```

Run with no keys, or with `DUKAAN_DEMO=1`, to replay the recorded searches (pinned to 12 Oct 2026). Tests: `uv run pytest`.

## How it uses SerpApi

| Engine | Used for | Cache |
| --- | --- | --- |
| `google_trends` TIMESERIES, `geo=IN-MH`, `today 3-m` | this season's interest, 5 items per call | 12 h |
| `google_trends` TIMESERIES, custom range around Diwali 2025 | season replay: growth still ahead, peak timing | 30 days |
| `google_shopping`, `location=Mumbai` | online price band for the 6 biggest movers | 24 h |
| `google_news` | price rises or shortages for the top picks | 12 h |
| `google_maps`, `ll=@19.0186,72.8424,15z` | supermarkets around the store | 7 days |
| `serpapi-search-tools` (shopping_search, news_search) | the agent's live lookups | 12 h |
| Account API | searches left (free) | none |

Every response is cached in SQLite, with the API key scrubbed out (SerpApi embeds it in pagination URLs).

## How an item gets its call

1. **Demand factor:**
   - Use the growth still ahead last season, if it is at least 1.2× and the peak hasn't passed yet. Otherwise use momentum: the last 7 days against 4–8 weeks ago.
   - Halve the factor towards 1 to stay cautious.
   - Clamp it between 0.6 and a category cap: festive 3.0, sweets 2.5, staples 1.3, dairy 1.2. More rangoli searches mean more rangoli sold; more salt searches don't mean three times the salt eaten.
   - Too few searches means the factor is 1.
2. **Target** = normal weekly stock × factor.
3. **The call:**
   - **Stock up** if the factor is at least 1.25 and stock is below target.
   - Otherwise **Restock** if stock is at half of normal or less.
   - Otherwise **Slow down** if the factor is at most 0.8 and stock is above normal.
   - Otherwise **OK**.

Reasons are templates in English and Hindi, so the numbers are never invented. The agent is told to use its tools and never make figures up.

## Code

| Path | What |
| --- | --- |
| `dukaan/store_seed.py` | the store (Dadar West) and its 50 starting items |
| `dukaan/inventory.py` | stock in SQLite (`data/store.sqlite`) |
| `dukaan/research.py` | the research run and the per-item calls |
| `dukaan/agent.py` | the stock agent: tools, TokenRouter loop, serpapi-search-tools |
| `dukaan/serp.py`, `signals.py`, `report.py`, `config.py` | cached SerpApi client, signal maths, action wording, festival calendar |
| `dukaan/app.py`, `templates/`, `static/` | FastAPI, the store page and the 3D Research Room (three.js) |
| `demo/` | recorded searches (API key scrubbed) for running without a key |
| `scripts/` | image fetcher, demo snapshot, screenshot helpers |

## Limits, honestly

- Search interest is a demand signal, not a sales forecast.
- Trends is read for Maharashtra; Google Trends has no city-level series for most of these items.
- Season replay assumes festivals keep a similar rhythm year to year. Diwali 2026 is 8 Nov.
- Online prices are a guide, not your wholesale rate.

## Credits and disclosures

- Product photos come from Wikipedia / Wikimedia Commons under free licences; sources are in `dukaan/static/items/credits.json`.
- Built during the hackathon window (from 11 Oct 2026) with AI assistance: Claude (Anthropic) helped design, write and test the code and wrote the Hindi text. The concept was drafted in Claude Design.
- Uses SerpApi, FastAPI, three.js, OpenAI SDK (via TokenRouter) and uv.
- MIT licence.
