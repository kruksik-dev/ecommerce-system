from fastapi import APIRouter, FastAPI
from producer import publish
from schemas import InventoryAddRequest, OrderRequest

app = FastAPI()


main_router = APIRouter(prefix="/main", tags=["Main"])
inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"])


@main_router.post("/orders")
def create_order(order: OrderRequest) -> dict[str, str]:
    publish("order_created", order.model_dump())
    return {"message": "Order received"}


@inventory_router.post("/new")
def add_new_inventory_item(item: InventoryAddRequest) -> dict[str, str]:
    publish("inventory_new_item", item.model_dump())
    return {"message": "New inventory item add request sent"}


app.include_router(main_router)
app.include_router(inventory_router)
