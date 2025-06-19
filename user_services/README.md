# User Service

This module is responsible for user management in the e-commerce system. It handles user registration via RabbitMQ queues.

## Features

- User registration (receives requests via the `user_register` queue, responds via `user_registered`)
- Stores users in a database (SQLModel)
- Password hashing (passlib)

## Queues

- **user_register** – receives user registration requests

## Requirements

- Python 3.10+
- RabbitMQ
- SQLModel, asyncpg, pika, passlib


## Project Structure

```
user_services/
├── app/
│   ├── consumer.py      # Logic for consuming messages from RabbitMQ
│   ├── database.py      # Database connection and operations
│   ├── models.py        # Database models
│   ├── setup_logger.py  # Logger configuration
├── Dockerfile           # Docker configuration
├── README.md            # Module documentation
```

## How to Run

1. Install dependencies:
    ```
    pip install sqlmodel asyncpg pika passlib[bcrypt]
    ```

2. Make sure RabbitMQ and the database are running.

3. Start the consumer:
    ```
    python app/consumer.py
    ```

## Communication Example

**User registration:**
- Send a JSON message to the `user_register` queue:
    ```json
    {
      "username": "janek",
      "email": "janek@example.com",
      "password": "secretpassword"
    }
    ```
- The response will appear on the `user_registered` queue:
    ```json
    {
      "success": true,
      "user_id": 1
    }
    ```


## Technologies

- **RabbitMQ**: Used for message passing between services.
- **PostgreSQL**: Database for storing order data.
- **SQLAlchemy**: ORM for database interactions.
- **Pika**: RabbitMQ client for Python.
