from sqlmodel import Session, SQLModel

from inventory_service.rabbitmq import RabbitMQClient
from inventory_service.repository import InventoryRepository
from inventory_service.database.db_engine import engine

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
