import asyncio
import json
import logging
import os
from threading import Thread
from typing import Any

import pika
from database import async_session, create_db_and_tables
from models import User
from passlib.hash import bcrypt
from setup_logger import setup_logging
from sqlalchemy import select

_logger = logging.getLogger(__name__)

RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")


async def register_user(data: dict[str, Any]) -> dict[str, bool | int | str]:
    _logger.info(f"Registering user: {data['username']}")

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == data["email"]))
        existing_user = result.scalars().first()

        if existing_user:
            _logger.warning(f"Email already registered: {data['email']}")
            return {"success": False, "error": "Email already exists"}

        user = User(
            username=data["username"],
            email=data["email"],
            password_hash=bcrypt.hash(data["password"]),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        _logger.info(f"User registered with ID: {user.id}")
        return {"success": True, "user_id": user.id}


def process_message(
    body: bytes,
    props: pika.BasicProperties,
    channel: pika.adapters.blocking_connection.BlockingChannel,
    loop: asyncio.AbstractEventLoop,
) -> bool:
    try:
        data: dict[str, Any] = json.loads(body)
        _logger.info(f"Processing user registration: {data}")

        future = asyncio.run_coroutine_threadsafe(register_user(data), loop)
        result = future.result(timeout=30)
        if props.reply_to:
            channel.basic_publish(
                exchange="",
                routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=json.dumps(result),
            )
        return True
    except Exception as e:
        _logger.error(f"Error processing user registration: {e}")
        return False


def consume_messages(loop: asyncio.AbstractEventLoop) -> None:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    queue_name = "user_register"
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    def on_message(ch, method, props, body) -> None:
        success = process_message(body, props, ch, loop)
        if method and method.delivery_tag is not None:
            if success:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue=queue_name, on_message_callback=on_message)
    _logger.info("Started consuming on 'user_register'")
    channel.start_consuming()


async def main() -> None:
    setup_logging()
    await create_db_and_tables()
    loop = asyncio.get_running_loop()
    Thread(target=consume_messages, args=(loop,), daemon=True).start()
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
