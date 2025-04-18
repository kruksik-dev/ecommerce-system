FROM python:3.13-alpine

WORKDIR /app

COPY /inventory_service /inventory_service
COPY shared /shared
COPY /inventory_service/src/inventory_service/consumer.py .
RUN pip install --upgrade pip
RUN pip install /shared
RUN pip install /inventory_service

CMD ["python", "/app/consumer.py"]
