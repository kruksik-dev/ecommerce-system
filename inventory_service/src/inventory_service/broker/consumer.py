import asyncio
import json

import aio_pika
from aio_pika.exceptions import AMQPConnectionError

from inventory_service.core.core import QUEUE_NAME, RABBITMQ_URL
from inventory_service.database.db_engine import get_session
from inventory_service.database.models import Product

RETRY_ATTEMPTS = 10
RETRY_DELAY = 3  # sekundy


async def handle_event(data: dict):
    product_id = data["product_id"]
    amount = data["amount"]

    async for session in get_session():
        product = await session.get(Product, product_id)
        if not product:
            print(f"Product {product_id} not found")
            return

        product.quantity += amount
        await session.commit()
        print(f"Product {product_id} quantity updated by {amount}")


async def start_worker():
    attempt = 0
    connection = None

    while attempt < RETRY_ATTEMPTS:
        try:
            print(f"[Worker] Connecting to RabbitMQ... attempt {attempt + 1}")
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            print("[Worker] Connected to RabbitMQ")
            break
        except AMQPConnectionError as e:
            print(f"[Worker] Connection failed: {e}")
            attempt += 1
            await asyncio.sleep(RETRY_DELAY)

    if not connection:
        print(
            "[Worker] Failed to connect to RabbitMQ after multiple attempts. Exiting worker."
        )
        return

    channel = await connection.channel()
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)

    async def process_message(message: aio_pika.IncomingMessage):
        async with message.process():
            data = json.loads(message.body)
            await handle_event(data)

    await queue.consume(process_message)
    print("[Worker] Waiting for messages...")
