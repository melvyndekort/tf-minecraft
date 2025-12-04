# Build stage
FROM python:3.14.1-alpine3.22 AS builder

RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN uv sync --frozen

# Runtime stage
FROM python:3.14.1-alpine3.22

COPY --from=builder /app/.venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /app
COPY src/ ./src/
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "minecraft_tools.idle_watcher.main"]
