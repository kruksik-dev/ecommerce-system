import os
import sys

from sqlmodel import Session, SQLModel, create_engine

from inventory_service.rabbitmq import RabbitMQClient
from inventory_service.repository import InventoryRepository

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@postgres:5432/inventory_db"
)
engine = create_engine(DATABASE_URL)


SQLModel.metadata.create_all(engine)

mq = RabbitMQClient(queue_name="order_created")


def handle_order_created(data):
    product_id = data["product_id"]
    quantity = data["quantity"]

    with Session(engine) as session:
        repo = InventoryRepository(session)
        success = repo.decrease_stock(product_id, quantity)

    if success:
        print(f"Stock updated for product {product_id}")
    else:
        print(f"Insufficient stock for product {product_id}")


if __name__ == "__main__":
    mq.consume(callback=handle_order_created)
