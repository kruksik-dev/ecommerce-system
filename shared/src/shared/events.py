import json
import os

import aio_pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL")


async def publish_event(routing_key: str, message: dict):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.default_exchange.publish(
        aio_pika.Message(body=json.dumps(message).encode()), routing_key=routing_key
    )
    await connection.close()
