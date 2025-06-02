FROM python:3.13-alpine

WORKDIR /app
COPY ./app /app

RUN pip install --no-cache-dir sqlmodel asyncpg pika dotenv colorlog

CMD ["python", "consumer.py"]
