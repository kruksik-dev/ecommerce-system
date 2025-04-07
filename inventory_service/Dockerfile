FROM python:3.13-alpine AS builder

WORKDIR /app

COPY ./inventory_service/pyproject.toml .
COPY ./inventory_service/README.md .
COPY ./inventory_service/src ./src

RUN pip install --no-cache-dir build \
    && python -m build --wheel --outdir dist

FROM python:3.13-alpine

WORKDIR /app

COPY --from=builder /app/dist/*.whl /app/
RUN pip install --no-cache-dir /app/*.whl
CMD ["uvicorn", "inventory_service.api.main:app", "--host", "0.0.0.0", "--port", "8000"]