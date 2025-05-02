import json
import os

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
