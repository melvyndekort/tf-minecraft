# Build stage
FROM python:3.13.7-slim AS builder

WORKDIR /app

RUN pip install poetry
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --only=main

# Runtime stage
FROM gcr.io/distroless/python3-debian12

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /app/site-packages
COPY src/dns_updater.py ./

ENV PYTHONPATH=/app/site-packages

CMD ["dns_updater.py"]
