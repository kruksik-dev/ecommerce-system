from pydantic import BaseModel


class Item(BaseModel):
    id: int
    quantity: int


class OrderCreatedEvent(BaseModel):
    order_id: int
    items: list[Item]
