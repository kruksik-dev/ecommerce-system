from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from shared.db import get_session, init_db
from shared.models import Product


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for application startup and shutdown."""
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/products/", response_model=Product)
async def create_product(
    product: Product, session: AsyncSession = Depends(get_session)
):
    db_product = Product(**product.dict())
    session.add(db_product)
    await session.commit()
    await session.refresh(db_product)
    return db_product


@app.get("/products/{product_id}", response_model=Product)
async def read_product(product_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product).where(Product.id == product_id))
    db_product = result.scalars().first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@app.get("/products/", response_model=list[Product])
async def read_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product))
    products = result.scalars().all()
    return products


@app.put("/products/{product_id}", response_model=Product)
async def update_product(
    product_id: int, product: Product, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Product).where(Product.id == product_id))
    db_product = result.scalars().first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    await session.commit()
    await session.refresh(db_product)
    return db_product


@app.delete("/products/{product_id}", response_model=Product)
async def delete_product(product_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product).where(Product.id == product_id))
    db_product = result.scalars().first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    await session.delete(db_product)
    await session.commit()
    return db_product
