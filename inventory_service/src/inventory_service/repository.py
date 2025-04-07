from sqlmodel import Session, select

from inventory_service.database.models import Product


class InventoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_product_by_id(self, product_id: int) -> Product | None:
        statement = select(Product).where(Product.id == product_id)
        return self.session.exec(statement).first()

    def add_product(self, product: Product) -> Product:
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return product

    def update_product(self, product: Product, update_product: Product) -> Product:
        for key, value in product.model_dump().items():
            setattr(update_product, key, value)
        self.session.commit()
        self.session.refresh(update_product)
        return update_product

    def delete_product(self, product: Product) -> Product:
        self.session.delete(product)
        self.session.commit()
        self.session.refresh(product)
        return product

    def decrease_stock(self, product: Product, quantity: int) -> Product | None:
        if product.is_in_stock() and product.decrease_stock(quantity):
            self.session.add(product)
            self.session.commit()
            self.session.refresh(product)
            return product
