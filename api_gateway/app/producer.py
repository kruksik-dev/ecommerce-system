import json
import os
import uuid

import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")


def publish(queue: str, message: dict):
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()


def publish_and_wait_for_response(queue: str, message: dict) -> dict:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    result = channel.queue_declare(queue="", exclusive=True)
    callback_queue = result.method.queue

    correlation_id = str(uuid.uuid4())
    response = None

    def on_response(ch, method, props, body) -> None:
        nonlocal response
        if props.correlation_id == correlation_id:
            response = json.loads(body)

    channel.basic_consume(
        queue=callback_queue, on_message_callback=on_response, auto_ack=True
    )

    channel.basic_publish(
        exchange="",
        routing_key=queue,
        properties=pika.BasicProperties(
            reply_to=callback_queue,
            correlation_id=correlation_id,
        ),
        body=json.dumps(message),
    )

    while response is None:
        connection.process_data_events()

    connection.close()
    return response
