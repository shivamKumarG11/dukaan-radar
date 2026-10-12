# Dukaan Radar for a public demo: replays the recorded SerpApi searches (no key needed).
# The stock agent runs when TOKENROUTER_API_KEY is set as a secret on the host.
FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.12.10
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
ENV DUKAAN_DEMO=1 AGENT_DAILY_LIMIT=150 PYTHONUNBUFFERED=1 PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uv run --no-dev uvicorn dukaan.app:app --host 0.0.0.0 --port ${PORT}"]
