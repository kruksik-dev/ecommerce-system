from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    quantity: int = 0
    description: str | None = None
    price: float = Field(default=0.0, ge=0.0)
