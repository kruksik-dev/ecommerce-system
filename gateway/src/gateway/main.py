from fastapi import FastAPI
from shared.events import publish_event
from shared.schemas import OrderCreatedEvent

app = FastAPI()


@app.post("/orders")
async def create_order(order: OrderCreatedEvent):
    await publish_event("order.created", order.model_dump())
    return {"status": "Order event published"}
