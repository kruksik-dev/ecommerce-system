FROM python:3.13-alpine AS builder

WORKDIR /app
COPY ../pyproject.toml ./pyproject.toml
COPY ../uv.lock ./uv.lock

RUN pip install --no-cache-dir uv \
    && uv venv \
    && . /app/.venv/bin/activate \
    && uv sync --no-dev

FROM python:3.13-alpine
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY ./inventory_service ./inventory_service

ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

CMD ["python", "inventory_service/main.py"]
