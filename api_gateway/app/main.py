from crud import get_all_users, get_user_by_id
from fastapi import APIRouter, FastAPI, HTTPException
from models import (
    InventoryAddRequest,
    OrderRequest,
    UserRegisterRequest,
    UserRegisterResponse,
    UserResponse,
)
from producer import publish, publish_and_wait_for_response

app = FastAPI()


main_router = APIRouter(prefix="/main", tags=["Orders"])
inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"])
user_router = APIRouter(prefix="/users", tags=["Users"])


@main_router.post("/orders")
def create_order(order: OrderRequest) -> dict[str, str]:
    publish("order_created", order.model_dump())
    return {"message": "Order received"}


@inventory_router.post("/new")
def add_new_inventory_item(item: InventoryAddRequest) -> dict[str, str]:
    publish("inventory_new_item", item.model_dump())
    return {"message": "New inventory item add request sent"}


@user_router.post("/register", response_model=UserRegisterResponse)
def register_user(user: UserRegisterRequest) -> UserRegisterResponse:
    result = publish_and_wait_for_response("user_register", user.model_dump())
    return UserRegisterResponse(**result)


@user_router.get("/", response_model=list[UserResponse])
async def get_users() -> list[UserResponse]:
    users_raw = await get_all_users()
    return users_raw


@user_router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    user_raw = await get_user_by_id(user_id)
    if user_raw is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_raw


app.include_router(main_router)
app.include_router(inventory_router)
app.include_router(user_router)
