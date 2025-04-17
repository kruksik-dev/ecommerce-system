import json

import aio_pika

from inventory_service.core.core import QUEUE_NAME, RABBITMQ_URL


async def publish_inventory_event(product_id: int, amount: int):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(QUEUE_NAME, durable=True)
        body = json.dumps({"product_id": product_id, "amount": amount})
        await channel.default_exchange.publish(
            aio_pika.Message(body=body.encode()), routing_key=QUEUE_NAME
        )
