# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install poetry
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --only=main --no-root

# Runtime stage
FROM python:3.14-alpine

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY src/bot.py ./

CMD ["python", "bot.py"]
