from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session

from inventory_service.database.models import Product
from inventory_service.repository import InventoryRepository
from inventory_service.database.db_engine import engine

app = FastAPI()


def get_session():
    with Session(engine) as session:
        yield session


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int, session: Session = Depends(get_session)) -> Product:
    repo = InventoryRepository(session)
    product = repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/products", response_model=Product)
def create_product(
    product: Product, session: Session = Depends(get_session)
) -> Product:
    repo = InventoryRepository(session)
    added_product = repo.add_product(product)
    return added_product


@app.patch("/products/{product_id}", response_model=Product)
def update_product(
    product_id: int, updated: Product, session: Session = Depends(get_session)
) -> Product:
    repo = InventoryRepository(session)
    product = repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updated.id = product_id
    updated_product = repo.update_product(product, updated)
    return updated_product


@app.delete("/products/{product_id}", response_model=Product)
def delete_product(product_id: int, session: Session = Depends(get_session)) -> Product:
    repo = InventoryRepository(session)
    product = repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    deleted_repo = repo.delete_product(product)
    return deleted_repo


@app.post("/products/{product_id}/decrease_stock", response_model=Product)
def decrease_stock(
    product_id: int, quantity: int, session: Session = Depends(get_session)
) -> Product:
    repo = InventoryRepository(session)
    product = repo.get_product_by_id(product_id)
    success = repo.decrease_stock(product, quantity)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    return success
