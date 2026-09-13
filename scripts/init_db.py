#!/usr/bin/env python3
# scripts/init_db.py
# Initialize the trading database schema
# Creates all tables from SQLAlchemy models

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "ml-trading-app-py")
)

from backend.config import settings
from backend.database.models import Base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine


async def init_db():
    """Create all database tables."""
    print("Initializing trading database...")
    print(f"Database URL: {settings.database_async_url}")

    try:
        engine = create_async_engine(settings.database_async_url, echo=False)

        async with engine.begin() as conn:
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("✓ Tables created successfully")

        await engine.dispose()
        print("✓ Database initialization complete")
        return 0

    except SQLAlchemyError as error:
        print(f"✗ Error initializing database: {error}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(init_db())
    sys.exit(exit_code)
