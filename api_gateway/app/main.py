from fastapi import FastAPI
from producer import publish
from schemas import OrderRequest

app = FastAPI()


@app.post("/orders")
def create_order(order: OrderRequest) -> dict[str, str]:
    publish("order_created", order.model_dump())
    return {"message": "Order received"}
