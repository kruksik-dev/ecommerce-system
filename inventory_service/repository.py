from sqlmodel import Session, select

from .models import Product


class InventoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_product_by_id(self, product_id: int) -> Product | None:
        statement = select(Product).where(Product.id == product_id)
        return self.session.exec(statement).first()

    def add_product(self, product: Product) -> None:
        self.session.add(product)
        self.session.commit()

    def update_product(self, product: Product) -> None:
        self.session.add(product)
        self.session.commit()

    def delete_product(self, product_id: int) -> None:
        product = self.get_product_by_id(product_id)
        if product:
            self.session.delete(product)
            self.session.commit()

    def decrease_stock(self, product_id: int, quantity: int) -> bool:
        product = self.get_product_by_id(product_id)
        if product and product.is_in_stock() and product.decrease_stock(quantity):
            self.session.add(product)
            self.session.commit()
            return True
        return False
