FROM python:3.13-alpine

WORKDIR /app
COPY ./app /app

RUN pip install --no-cache-dir fastapi[all] pika sqlalchemy aiosqlite asyncpg

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
