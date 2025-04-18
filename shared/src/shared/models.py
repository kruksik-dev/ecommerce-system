from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    pid: int
    stock: int
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    price: float
