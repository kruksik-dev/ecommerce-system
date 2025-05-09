# E-commerce System

The E-commerce System is a microservices-based application designed to handle various aspects of an e-commerce platform. It consists of multiple services that communicate with each other using RabbitMQ and interact with a PostgreSQL database.

## Services

### 1. API Gateway
- Handles HTTP requests and acts as the entry point for the system.
- Built with **FastAPI**.
- Publishes messages to RabbitMQ for further processing by other services.

### 2. Order Services
- Processes orders by consuming messages from RabbitMQ.
- Interacts with the PostgreSQL database to store and retrieve order data.
- Provides logging for better traceability.

## Requirements

- **Python**: 3.13
- **Docker**: For containerized deployment.
- **RabbitMQ**: Message broker for inter-service communication.
- **PostgreSQL**: Database for storing application data.

## Running the Application

### Using Docker Compose
1. Build and start all services:
   ```bash
   docker-compose up --build
   ```
2. Access the API Gateway at:
   ```
   http://localhost:5000
   ```

### Stopping the Application
To stop all services, run:
```bash
docker-compose down
```

## Technologies

- **FastAPI**: Framework for building APIs.
- **RabbitMQ**: Message broker for communication between services.
- **PostgreSQL**: Relational database for data storage.
- **Docker**: Containerization platform for deployment.
