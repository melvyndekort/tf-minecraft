# Build stage
FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install poetry
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --only=main

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/bot.py ./
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# AWS configuration
RUN mkdir -p /home/appuser/.aws && chown -R appuser:appuser /home/appuser/.aws

ENV AWS_PROFILE=botrole

USER appuser

ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "bot.py"]
