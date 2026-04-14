import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# Module-level pool — created once at server startup, shared across all requests
_pool: asyncpg.Pool = None

async def init_pool():
    """Create the connection pool. Called once when the server starts."""
    global _pool
    _pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "brand_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "password"),
        min_size=2,   # Always keep 2 connections open and ready
        max_size=10,  # Allow up to 10 simultaneous connections under heavy load
    )
    print("✅ Database connection pool initialized.")

async def close_pool():
    """Gracefully close the pool. Called once when the server shuts down."""
    global _pool
    if _pool:
        await _pool.close()
        print("🔌 Database connection pool closed.")

async def run_query(sql: str, params=None):
    """
    Execute a read-only SQL query using a pooled connection.
    The connection is automatically returned to the pool when done.
    """
    # Enforce read-only constraint
    forbidden_keywords = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE "]
    if any(keyword in sql.upper() for keyword in forbidden_keywords):
        raise ValueError("Only SELECT queries are allowed.")

    # Borrow a connection from the pool, run the query, then return it automatically
    async with _pool.acquire() as conn:
        rows = await conn.fetch(sql, *(params or []))
        # asyncpg returns Record objects — convert to plain dicts for JSON serialisation
        return [dict(row) for row in rows]
