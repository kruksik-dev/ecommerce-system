from datetime import datetime

from sqlmodel import Field, SQLModel


class Inventory(SQLModel, table=True):
    __tablename__ = "inventory"
    id: int = Field(default=None, primary_key=True)
    quantity: int
    description: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now)
