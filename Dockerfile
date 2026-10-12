# Dukaan Radar on Hugging Face Spaces (Docker) or any container host.
# Secrets on the host: SERPAPI_API_KEY (live searches, capped per day; without it the recording replays)
# and TOKENROUTER_API_KEY (the stock agent).
FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.12.10
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
# Spaces run the container as user 1000: the stock and search cache folders must be writable
RUN mkdir -p data cache && chmod -R 777 data cache
ENV PATH=/app/.venv/bin:$PATH SERPAPI_DAILY_LIMIT=40 AGENT_DAILY_LIMIT=150 PYTHONUNBUFFERED=1 PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn dukaan.app:app --host 0.0.0.0 --port ${PORT}"]
