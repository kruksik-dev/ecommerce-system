FROM python:3.13-alpine

WORKDIR /app

COPY /database_service /database_service

COPY shared /shared

RUN pip install --upgrade pip
RUN pip install /shared
RUN pip install /database_service

CMD ["uvicorn", "database_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
