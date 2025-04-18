import asyncio
import json

import aio_pika
from sqlmodel import select

from shared.db import get_session
from shared.events import RABBITMQ_URL
from shared.models import Product
from shared.schemas import OrderCreatedEvent


async def handle_order_created(event: OrderCreatedEvent) -> None:
    print(f"[Inventory] Handling order: {event.order_id}")
    async with get_session() as session:
        for item in event.items:
            result = await session.exec(select(Product).where(Product.id == item.id))
            product = result.one_or_none()
            if product:
                product.stock -= item.quantity
                session.add(product)
        await session.commit()


async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    exchange = await channel.declare_exchange(
        "orders", aio_pika.ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue("order.created", durable=True)

    try:
        await queue.bind(exchange, routing_key="order.created")
    except Exception as e:
        print(f"[Error] Failed to bind queue: {e}")
        raise

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                payload = json.loads(message.body)
                event = OrderCreatedEvent(**payload)
                await handle_order_created(event)


if __name__ == "__main__":
    asyncio.run(main())
