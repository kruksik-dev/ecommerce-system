from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from inventory_service.database.db_engine import get_session, init_db
from inventory_service.database.models import Product
from inventory_service.repository import InventoryRepository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for application startup and shutdown."""
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/products/{product_id}", response_model=Product)
async def get_product(
    product_id: int, session: AsyncSession = Depends(get_session)
) -> Product:
    repo = InventoryRepository(session)
    product = await repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/products", response_model=list[Product])
async def get_all_products(
    session: AsyncSession = Depends(get_session),
) -> list[Product]:
    repo = InventoryRepository(session)
    products = await repo.get_all_products()
    return products


@app.post("/products", response_model=Product)
async def create_product(
    product: Product, session: AsyncSession = Depends(get_session)
) -> Product:
    repo = InventoryRepository(session)
    added_product = await repo.add_product(product)
    return added_product


@app.patch("/products/{product_id}", response_model=Product)
async def update_product(
    product_id: int, updated: Product, session: AsyncSession = Depends(get_session)
) -> Product:
    repo = InventoryRepository(session)
    product = await repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updated.id = product_id
    updated_product = await repo.update_product(product, updated)
    return updated_product


@app.delete("/products/{product_id}", response_model=Product)
async def delete_product(
    product_id: int, session: AsyncSession = Depends(get_session)
) -> Product:
    repo = InventoryRepository(session)
    product = await repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    deleted_product = await repo.delete_product(product)
    return deleted_product


@app.post("/products/{product_id}/decrease_stock", response_model=Product)
async def decrease_stock(
    product_id: int, quantity: int, session: AsyncSession = Depends(get_session)
) -> Product:
    repo = InventoryRepository(session)
    product = await repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updated_product = await repo.decrease_stock(product, quantity)
    if not updated_product:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    return updated_product
