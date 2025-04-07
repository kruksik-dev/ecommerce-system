from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from inventory_service.database.models import Product


class InventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_product_by_id(self, product_id: int) -> Product | None:
        statement = select(Product).where(Product.id == product_id)
        result = await self.session.exec(statement)
        return result.one_or_none()

    async def get_all_products(self) -> list[Product]:
        statement = select(Product)
        result = await self.session.exec(statement)
        return list(result)

    async def add_product(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update_product(
        self, product: Product, updated_product: Product
    ) -> Product:
        for key, value in updated_product.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete_product(self, product: Product) -> Product:
        await self.session.delete(product)
        await self.session.commit()
        return product

    async def decrease_stock(self, product: Product, quantity: int) -> Product | None:
        if product.is_in_stock() and product.decrease_stock(quantity):
            self.session.add(product)
            await self.session.commit()
            await self.session.refresh(product)
            return product
        return None
