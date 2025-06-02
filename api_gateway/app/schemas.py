from typing import Optional

from pydantic import BaseModel


class OrderRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int


class InventoryAddRequest(BaseModel):
    quantity: int
    description: Optional[str] = None
