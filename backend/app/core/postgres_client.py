"""
PostgreSQL Client — EnterpriseMind AI.

Async PostgreSQL connection pool using asyncpg.
Replaces Supabase client for local/self-hosted deployment.

Usage:
    from app.core.postgres_client import get_pool, execute_query, fetch_one, fetch_all
"""
import logging
import os

import asyncpg

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create asyncpg connection pool (singleton)."""
    global _pool
    if _pool is None:
        database_url = settings.DATABASE_URL
        logger.info("Creating PostgreSQL connection pool...")
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=20,
            command_timeout=60,
        )
        logger.info("PostgreSQL pool created successfully.")
    return _pool


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed.")


async def execute_query(query: str, *args) -> str:
    """Execute a query (INSERT, UPDATE, DELETE). Returns status string."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(query, *args)
        return result


async def fetch_one(query: str, *args) -> dict | None:
    """Fetch a single row as dict. Returns None if no rows."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> list[dict]:
    """Fetch all rows as list of dicts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def fetch_val(query: str, *args):
    """Fetch a single value."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)
