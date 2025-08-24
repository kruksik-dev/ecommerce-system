# Inventory Service

This module manages inventory for the e-commerce system. It handles inventory checks and updates via RabbitMQ queues.

## Features

- Inventory validation for orders (receives requests via the `order_validate` queue, responds via `order_validate_response`)
- Adding new inventory items (via the `inventory_new_item` queue)
- Stores inventory data in a database (SQLModel)
- Asynchronous database operations

## Queues

- **order_validate** – receives requests to validate and update inventory for orders
- **order_validate_response** – sends responses to order validation requests
- **inventory_new_item** – receives requests to add new inventory items

## Requirements

- Python 3.10+
- RabbitMQ
- SQLModel, asyncpg, pika

## Project Structure

```
inventory_service/
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
    pip install sqlmodel asyncpg pika
    ```

2. Make sure RabbitMQ and the database are running.

3. Start the consumer:
    ```
    python app/consumer.py
    ```

## Communication Example

**Order validation:**
- Send a JSON message to the `order_validate` queue:
    ```json
    {
      "order_id": 123,
      "product_id": 1,
      "quantity": 2
    }
    ```
- The response will appear on the `order_validate_response` queue:
    ```json
    {
      "order_id": 123,
      "success": true,
      "message": "Inventory updated",
      "order_data": {
        "order_id": 123,
        "product_id": 1,
        "quantity": 2
      }
    }
    ```

**Add new inventory item:**
- Send a JSON message to the `inventory_new_item` queue:
    ```json
    {
      "quantity": 10,
      "description": "Blue T-shirt, size M"
    }
    ```

## Technologies

- **RabbitMQ**: Used for message passing between services.
- **PostgreSQL**: Database for storing inventory data.
- **SQLModel**: ORM for database interactions.
- **Pika**: RabbitMQ client for Python.
