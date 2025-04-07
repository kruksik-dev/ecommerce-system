import os
from typing import Final

from sqlmodel import create_engine

DATABASE_URL: Final = os.getenv(
    "DATABASE_URL", "postgresql://user:password@postgres:5432/inventory_db"
)
engine: Final = create_engine(DATABASE_URL)
