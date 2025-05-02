import asyncio
import json
import logging
import os
import time
from threading import Thread

import pika
from database import create_db_and_tables, async_session
from models import Order

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")


async def save_order(data: dict) -> None:
    async with async_session() as session:
        order = Order(**data)
        session.add(order)
        await session.commit()
        await session.refresh(order)  # zapewnia dostęp do pola `id`
        print(f"[+] Order saved: {order.id}")


def process_message(body, loop):
    """Process a single RabbitMQ message"""
    try:
        data = json.loads(body)
        logger.info(f"Processing order: {data}")

        # Run async save_order in the event loop
        future = asyncio.run_coroutine_threadsafe(save_order(data), loop)
        future.result(timeout=30)  # Wait for completion
        return True
    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        return False


def consume_messages(loop):
    """Synchronously consume messages from RabbitMQ"""
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            channel = connection.channel()

            channel.queue_declare(queue="order_created", durable=True)
            channel.basic_qos(prefetch_count=1)

            for method, properties, body in channel.consume("order_created"):
                success = process_message(body, loop)

                if success:
                    channel.basic_ack(method.delivery_tag)
                else:
                    channel.basic_nack(method.delivery_tag, requeue=False)

        except pika.exceptions.AMQPError as e:
            logger.error(f"RabbitMQ error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)


async def main():
    """Initialize and start the consumer"""
    await create_db_and_tables()

    # Run RabbitMQ consumer in a separate thread
    loop = asyncio.get_running_loop()
    Thread(target=consume_messages, args=(loop,), daemon=True).start()

    # Keep the main thread alive
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
