FROM python:3.13-alpine

WORKDIR /app

COPY /gateway /gateway

COPY shared /shared

RUN pip install --upgrade pip
RUN pip install /shared
RUN pip install /gateway

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
