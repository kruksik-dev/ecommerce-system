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
