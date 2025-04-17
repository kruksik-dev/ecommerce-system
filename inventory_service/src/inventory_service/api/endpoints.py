from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from inventory_service.broker.publisher import publish_inventory_event
from inventory_service.database.db_engine import get_session
from inventory_service.database.models import Product

router = APIRouter()


@router.post("/products/", response_model=Product)
async def create_product(
    product: Product, session: AsyncSession = Depends(get_session)
) -> Product:
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


@router.post("/products/{product_id}/increase/")
async def increase_quantity(product_id: int, amount: int):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    await publish_inventory_event(product_id, amount)
    return {"msg": "Increase event sent"}


@router.post("/products/{product_id}/decrease/")
async def decrease_quantity(product_id: int, amount: int):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    await publish_inventory_event(product_id, -amount)
    return {"msg": "Decrease event sent"}


@router.get("/products/", response_model=list[Product])
async def list_products(session: AsyncSession = Depends(get_session)) -> list[Product]:
    result = await session.execute(select(Product))
    return list(result.scalars().all())
