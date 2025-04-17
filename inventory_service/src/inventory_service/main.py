from contextlib import asynccontextmanager

from fastapi import FastAPI

from inventory_service.api.endpoints import router as api_router
from inventory_service.database.db_engine import init_db
from inventory_service.broker.consumer import start_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    import asyncio

    asyncio.create_task(start_worker())
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(api_router, prefix="/api")
