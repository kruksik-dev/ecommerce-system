from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    quantity: int = 0
    description: str | None = None
    price: float = Field(default=0.0, ge=0.0)

    def is_in_stock(self) -> bool:
        return self.quantity > 0

    def decrease_stock(self, quantity: int) -> bool:
        if self.quantity >= quantity:
            self.quantity -= quantity
            return True
        return False
