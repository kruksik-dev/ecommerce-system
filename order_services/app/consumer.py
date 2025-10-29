import asyncio
import json
import logging
import os
import uuid
from threading import Thread
from typing import Any

import pika
from database import async_session, create_db_and_tables
from models import Order
from setup_logger import setup_logging

_logger = logging.getLogger(__name__)

RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")


async def save_order(data: dict[str, Any]) -> Order:
    _logger.info(f"Processing save_order: {data}")
    async with async_session() as session:
        order = Order(**data)
        session.add(order)
        await session.commit()
        await session.refresh(order)
        _logger.info(f"Order saved: {order.id}")
        return order


def validate_inventory(data: dict[str, Any]) -> tuple[bool, str]:
    """Send validation request to inventory_service and wait for response."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    callback_queue = "order_validate_response"
    channel.queue_declare(queue=callback_queue, durable=True)
    corr_id = str(uuid.uuid4())

    order_data = {
        "order_id": corr_id,
        "product_id": data["product_id"],
        "quantity": data["quantity"],
    }

    channel.basic_publish(
        exchange="",
        routing_key="order_validate",
        properties=pika.BasicProperties(
            reply_to=callback_queue,
            correlation_id=corr_id,
        ),
        body=json.dumps(order_data),
    )

    response = {}

    def on_response(ch, method, props, body) -> None:
        if props.correlation_id == corr_id:
            nonlocal response
            response = json.loads(body)
            ch.stop_consuming()

    channel.basic_consume(
        queue=callback_queue, on_message_callback=on_response, auto_ack=True
    )

    channel.start_consuming()
    connection.close()
    return response.get("success", False), response.get("message", "")


def process_message(
    body: bytes,
    props: pika.BasicProperties,
    channel: pika.adapters.blocking_connection.BlockingChannel,
    loop: asyncio.AbstractEventLoop,
) -> bool:
    try:
        data: dict[str, Any] = json.loads(body)
        _logger.info(f"Processing order: {data}")

        valid, message = validate_inventory(data)
        _logger.info(f"Valid: {valid}, Message: {message}")
        if not valid:
            response = {
                "order_id": None,
                "success": False,
                "message": f"Order failed: {message}",
                "order_data": data,
                "created_at": None,
            }
            if props.reply_to:
                channel.basic_publish(
                    exchange="",
                    routing_key=props.reply_to,
                    properties=pika.BasicProperties(
                        correlation_id=props.correlation_id
                    ),
                    body=json.dumps(response),
                )
            _logger.warning(f"Inventory validation failed: {message}")
            return False

        future = asyncio.run_coroutine_threadsafe(save_order(data), loop)
        order: Order = future.result(timeout=30)
        response = {
            "order_id": order.id,
            "success": True,
            "message": "Order created successfully",
            "order_data": data,
            "created_at": order.created_at.isoformat()
            if hasattr(order, "created_at") and order.created_at
            else None,
        }
        if props.reply_to:
            channel.basic_publish(
                exchange="",
                routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=json.dumps(response),
            )
        return True
    except Exception as e:
        _logger.error(f"Failed to process message: {e}")
        response = {
            "order_id": None,
            "success": False,
            "message": f"Order failed: {str(e)}",
            "order_data": None,
            "created_at": None,
        }
        if props and hasattr(props, "reply_to") and props.reply_to:
            channel.basic_publish(
                exchange="",
                routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=json.dumps(response),
            )
        return False


def consume_messages(loop: asyncio.AbstractEventLoop) -> None:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    queue_name = "order_created"
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
    _logger.info("Started consuming on 'order_created'")
    channel.start_consuming()


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
