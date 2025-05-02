import asyncio
import json
import logging
import os
import time
from threading import Thread

import pika
from database import create_db_and_tables, get_session
from models import Order

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RECONNECT_DELAY = 5  # seconds between connection attempts


async def save_order(data: dict) -> None:
    try:
        session = await get_session()
        async with session.begin():
            order = Order(**data)
            session.add(order)
        logger.info(f"Order saved successfully: {order.id}")
    except Exception as e:
        logger.error(f"Failed to save order: {e}")
        raise


def connect_to_rabbitmq():
    retries = 5
    delay = 1

    for attempt in range(retries):
        try:
            connection_params = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                connection_attempts=5,
                retry_delay=5,
                socket_timeout=5,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            connection = pika.BlockingConnection(connection_params)
            logger.info("Successfully connected to RabbitMQ")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            if attempt < retries - 1:
                logger.warning(
                    f"Connection failed (attempt {attempt + 1}/{retries}): {e}. Retrying in {delay} seconds..."
                )
                time.sleep(delay)
                delay *= 2
            else:
                logger.error(
                    "Maximum retry attempts reached. Could not connect to RabbitMQ."
                )
                raise


def start_consuming(loop):
    while True:
        try:
            connection = connect_to_rabbitmq()
            channel = connection.channel()

            # Declare queue with durable=True
            channel.queue_declare(queue="order_created", durable=True)
            channel.basic_qos(prefetch_count=1)

            def callback(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    logger.info(f"Received message: {data}")

                    # Run the coroutine in the event loop
                    future = asyncio.run_coroutine_threadsafe(save_order(data), loop)

                    # Wait for the future to complete and handle result/exception
                    try:
                        future.result(timeout=30)  # Wait up to 30 seconds
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        logger.info(
                            f"Message processed and acknowledged: {method.delivery_tag}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to process message: {e}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except Exception as e:
                    logger.error(f"Unexpected error processing message: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_consume(
                queue="order_created", on_message_callback=callback, auto_ack=False
            )

            logger.info(
                "Waiting for messages in 'order_created' queue. To exit press CTRL+C"
            )
            channel.start_consuming()

        except pika.exceptions.ConnectionClosedByBroker:
            logger.warning("Connection closed by broker. Reconnecting...")
            time.sleep(RECONNECT_DELAY)
            continue
        except pika.exceptions.AMQPChannelError as err:
            logger.error(f"Channel error: {err}. Reconnecting...")
            time.sleep(RECONNECT_DELAY)
            continue
        except pika.exceptions.AMQPConnectionError:
            logger.error("Connection was closed. Reconnecting...")
            time.sleep(RECONNECT_DELAY)
            continue
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
            try:
                if connection and connection.is_open:
                    connection.close()
            except Exception as e:
                logger.error(f"Error while closing connection: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(RECONNECT_DELAY)
            continue


async def consume_async():
    await create_db_and_tables()

    loop = asyncio.get_running_loop()
    thread = Thread(target=start_consuming, args=(loop,), daemon=True)
    thread.start()

    try:
        while thread.is_alive():
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Shutting down consumer...")
    except Exception as e:
        logger.error(f"Error in consume_async: {e}")


def consume():
    try:
        asyncio.run(consume_async())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
