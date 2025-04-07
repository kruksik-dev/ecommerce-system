import json
from typing import Callable

import pika


class RabbitMQClient:
    def __init__(self, queue_name: str) -> None:
        self.queue_name: str = queue_name
        self.connection: pika.BlockingConnection = pika.BlockingConnection(
            pika.ConnectionParameters(host="rabbitmq")
        )
        self.channel: pika.adapters.blocking_connection.BlockingChannel = (
            self.connection.channel()
        )
        self.channel.queue_declare(queue=queue_name)

    def publish(self, message: dict, routing_key: str) -> None:
        self.channel.basic_publish(
            exchange="", routing_key=routing_key, body=json.dumps(message)
        )

    def consume(self, callback: Callable[[dict], None]) -> None:
        def wrapper(
            ch: pika.adapters.blocking_connection.BlockingChannel,
            method: pika.spec.Basic.Deliver,
            properties: pika.spec.BasicProperties,
            body: bytes,
        ) -> None:
            data = json.loads(body)
            callback(data)

        self.channel.basic_consume(
            queue=self.queue_name, on_message_callback=wrapper, auto_ack=True
        )
        print("Waiting for messages...")
        self.channel.start_consuming()
