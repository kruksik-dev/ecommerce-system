from datetime import datetime

from sqlmodel import Field, SQLModel


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    id: int = Field(default=None, primary_key=True)
    user_id: int
    product_id: int
    quantity: int
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.now)
