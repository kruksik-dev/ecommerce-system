import asyncio
import json
import logging
import os
import time
from threading import Thread
from typing import Any

import pika
from database import async_session, create_db_and_tables
from models import Order
from setup_logger import setup_logging

_logger = logging.getLogger(__name__)

RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")


async def save_order(data: dict[str, Any]) -> None:
    async with async_session() as session:
        order = Order(**data)
        session.add(order)
        await session.commit()
        await session.refresh(order)
        _logger.info(f"Order saved: {order.id}")


def process_message(body: bytes, loop: asyncio.AbstractEventLoop) -> bool:
    """Process a single RabbitMQ message"""
    try:
        data: dict[str, Any] = json.loads(body)
        _logger.info(f"Processing order: {data}")
        future = asyncio.run_coroutine_threadsafe(save_order(data), loop)
        future.result(timeout=30)
        return True
    except Exception as e:
        _logger.error(f"Failed to process message: {e}")
        return False


def consume_messages(loop: asyncio.AbstractEventLoop) -> None:
    """Synchronously consume messages from RabbitMQ"""
    while True:
        try:
            connection: pika.BlockingConnection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            channel: pika.adapters.blocking_connection.BlockingChannel = (
                connection.channel()
            )

            channel.queue_declare(queue="order_created", durable=True)
            channel.basic_qos(prefetch_count=1)

            for method, *_, body in channel.consume("order_created"):
                success: bool = process_message(body, loop)

                if method and method.delivery_tag is not None:
                    if success:
                        channel.basic_ack(method.delivery_tag)
                    else:
                        channel.basic_nack(method.delivery_tag, requeue=False)
        except Exception as e:
            _logger.warning(f"Unexpected error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)


async def main() -> None:
    """Initialize and start the consumer"""
    setup_logging()
    await create_db_and_tables()

    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    Thread(target=consume_messages, args=(loop,), daemon=True).start()

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
