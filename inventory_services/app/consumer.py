import asyncio
import json
import logging
import os
from threading import Thread
from typing import Any

import pika
from database import async_session, create_db_and_tables
from models import Inventory
from setup_logger import setup_logging
from sqlmodel import select

_logger = logging.getLogger(__name__)

RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")


async def check_and_update_inventory(data: dict[str, Any]) -> dict[str, Any]:
    _logger.info(f"Checking inventory for order: {data}")
    async with async_session() as session:
        product_id = data["product_id"]
        quantity = data["quantity"]
        result = await session.execute(
            select(Inventory).where(Inventory.id == product_id).with_for_update()
        )
        inv = result.scalar_one_or_none()
        if not inv:
            _logger.warning(f"Product not found: {product_id}")
            return {"success": False, "message": "Product not found"}
        if inv.quantity < quantity:
            _logger.warning(
                f"Not enough inventory for product {product_id}. Needed: {quantity}, Available: {inv.quantity}"
            )
            return {"success": False, "message": "Not enough inventory"}
        inv.quantity -= quantity
        session.add(inv)
        await session.commit()
        _logger.info(
            f"Inventory updated for product {product_id}. Remaining: {inv.quantity}"
        )
        return {"success": True, "message": "Inventory updated"}


async def add_new_item(data: dict[str, Any]) -> Inventory:
    _logger.info(f"Adding new item to inventory: {data}")
    async with async_session() as session:
        quantity = data["quantity"]
        description = data.get("description")
        inv = Inventory(quantity=quantity, description=description)
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        _logger.info(f"New item committed to database: {inv}")
        return inv


def process_order_validate(ch, method, props, body, loop) -> None:
    try:
        data: dict[str, Any] = json.loads(body)
        _logger.info(f"Received order_validate message: {data}")
        future = asyncio.run_coroutine_threadsafe(
            check_and_update_inventory(data), loop
        )
        result = future.result(timeout=30)
        response = {
            "order_id": data.get("order_id"),
            "success": result["success"],
            "message": result["message"],
            "order_data": data,
        }
        ch.basic_publish(
            exchange="",
            routing_key=props.reply_to if props.reply_to else "order_validate_response",
            properties=pika.BasicProperties(correlation_id=props.correlation_id),
            body=json.dumps(response),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        _logger.info(f"Processed order_validate: {response}")
    except Exception as e:
        _logger.error(f"Failed to process order_validate: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def process_inventory_new_item(ch, method, props, body, loop) -> None:
    try:
        data = json.loads(body)
        _logger.info(f"Received inventory_new_item message: {data}")
        future = asyncio.run_coroutine_threadsafe(add_new_item(data), loop)
        inv = future.result(timeout=30)
        response = {
            "id": inv.id,
            "quantity": inv.quantity,
            "description": inv.description,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        ch.basic_publish(
            exchange="",
            routing_key=props.reply_to
            if props.reply_to
            else "inventory_new_item_response",
            properties=pika.BasicProperties(correlation_id=props.correlation_id),
            body=json.dumps(response),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        _logger.info(f"New inventory item added: {data}")
    except Exception as e:
        _logger.error(f"Failed to add new inventory item: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def consume_messages(loop: asyncio.AbstractEventLoop) -> None:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue="order_validate", durable=True)
    channel.queue_declare(queue="inventory_new_item", durable=True)
    channel.basic_qos(prefetch_count=1)

    def on_order_validate(ch, method, props, body):
        process_order_validate(ch, method, props, body, loop)

    def on_inventory_new_item(ch, method, props, body):
        process_inventory_new_item(ch, method, props, body, loop)

    channel.basic_consume(queue="order_validate", on_message_callback=on_order_validate)
    channel.basic_consume(
        queue="inventory_new_item", on_message_callback=on_inventory_new_item
    )
    _logger.info("Started consuming on 'order_validate' and 'inventory_new_item'")
    channel.start_consuming()


async def main() -> None:
    setup_logging()
    _logger.info("Starting inventory service...")
    await create_db_and_tables()
    _logger.info("Database initialized.")

    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    Thread(target=consume_messages, args=(loop,), daemon=True).start()

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
