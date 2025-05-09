# API Gateway

The API Gateway module is responsible for handling HTTP requests and facilitating communication with other services in the e-commerce system. It is built using the **FastAPI** framework and integrates with **RabbitMQ** for message passing between services.

## Features

- **Order Handling**: Accepts order creation requests and forwards them to the RabbitMQ queue.
- **RabbitMQ Integration**: Publishes messages to the queue for further processing by other microservices.

## Project Structure

```
api_gateway/
├── app/
│   ├── main.py          # Main FastAPI application
│   ├── producer.py      # Logic for publishing messages to RabbitMQ
│   ├── schemas.py       # Data schemas (Pydantic)
├── Dockerfile           # Docker configuration
├── README.md            # Module documentation
```

## Endpoints

### POST `/orders`

Creates a new order and sends it to the RabbitMQ queue.

#### Example Request:
```json
POST /orders HTTP/1.1
Content-Type: application/json

{
  "user_id": 1,
  "product_id": 42,
  "quantity": 3
}
```

#### Example Response:
```json
{
  "message": "Order received"
}
```

## Requirements

- **Python**: 3.13
- **RabbitMQ**: A RabbitMQ host must be accessible (default: `rabbitmq`).

## Running the Application

### Locally
1. Install dependencies:
   ```bash
   pip install fastapi[all] pika
   ```
2. Run the application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### Using Docker
1. Build the Docker image:
   ```bash
   docker build -t api_gateway .
   ```
2. Run the container:
   ```bash
   docker run -p 8000:8000 --env RABBITMQ_HOST=<rabbitmq_host> api_gateway
   ```

## RabbitMQ Configuration

RabbitMQ is used for message passing between services. The default RabbitMQ host can be configured using the `RABBITMQ_HOST` environment variable.

## Technologies

- **FastAPI**: Framework for building APIs.
- **RabbitMQ**: Message queue system for inter-service communication.
- **Pika**: RabbitMQ client for Python.
