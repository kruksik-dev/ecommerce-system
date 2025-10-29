from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OrderRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int


class InventoryAddRequest(BaseModel):
    quantity: int
    description: Optional[str] = None


class UserRegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class UserRegisterResponse(BaseModel):
    success: bool
    user_id: int | None = None
    error: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        orm_mode = True


class OrderCreateResponse(BaseModel):
    order_id: int | None = None
    success: bool
    message: str
    order_data: dict | None = None


class InventoryAddResponse(BaseModel):
    id: int
    quantity: int
    description: str | None = None
    created_at: str
