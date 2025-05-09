# Order Services

The Order Services module is responsible for processing orders in the e-commerce system. It consumes messages from RabbitMQ, interacts with the database, and manages order-related operations.

## Features

- **Message Consumption**: Listens to RabbitMQ queues for incoming order messages.
- **Database Integration**: Handles database operations for storing and retrieving order data.
- **Logging**: Provides structured logging for better traceability and debugging.

## Project Structure

```
order_services/
├── app/
│   ├── consumer.py      # Logic for consuming messages from RabbitMQ
│   ├── database.py      # Database connection and operations
│   ├── models.py        # Database models
│   ├── setup_logger.py  # Logger configuration
├── Dockerfile           # Docker configuration
├── README.md            # Module documentation
```

## Requirements

- **Python**: 3.13
- **RabbitMQ**: A RabbitMQ host must be accessible (default: `rabbitmq`).
- **PostgreSQL**: A PostgreSQL database must be accessible for storing order data.

## Running the Application

### Locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python app/consumer.py
   ```

### Using Docker
1. Build the Docker image:
   ```bash
   docker build -t order_services .
   ```
2. Run the container:
   ```bash
   docker run --env DATABASE_URL=<database_url> --env RABBITMQ_HOST=<rabbitmq_host> order_services
   ```

## Environment Variables

- `DATABASE_URL`: The connection string for the PostgreSQL database (e.g., `postgresql+asyncpg://user:password@host:port/dbname`).
- `RABBITMQ_HOST`: The hostname or IP address of the RabbitMQ server.

## Technologies

- **RabbitMQ**: Used for message passing between services.
- **PostgreSQL**: Database for storing order data.
- **SQLAlchemy**: ORM for database interactions.
- **Pika**: RabbitMQ client for Python.
