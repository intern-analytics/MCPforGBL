import os
import sys
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# We now maintain separate tenant dynamic connection pools instead of a singular master one
_pools: dict[str, asyncpg.Pool] = {}

async def get_pool(db_user: str, db_pass: str) -> asyncpg.Pool:
    """Retrieves or instantly initializes a connection pool tailored to the requested DB credentials."""
    global _pools
    
    # Fallback default user structure to system envs if for some reason None reaches deep
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "brand_db")
    username = db_user or os.getenv("DB_USER", "postgres")
    password = db_pass or os.getenv("DB_PASS", "password")

    if username not in _pools:
        print(f"Initializing new dynamic connection pool for tenant '{username}'...", file=sys.stderr)
        _pools[username] = await asyncpg.create_pool(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            min_size=1,   
            max_size=7,   
        )
        print(f"Active pool established for '{username}'.", file=sys.stderr)
    
    return _pools[username]

async def close_all_pools():
    """Gracefully closes all tenant connection pools. Called on Server shutdown."""
    global _pools
    for username, pool in _pools.items():
        await pool.close()
    _pools.clear()
    print("All tenant database connection pools closed.", file=sys.stderr)

async def run_query(sql: str, params=None, db_user: str = None, db_pass: str = None):
    """
    Executes a read-only SQL query explicitly bounded to a specific tenant connection pool.
    """
    forbidden_keywords = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE "]
    if any(keyword in sql.upper() for keyword in forbidden_keywords):
        raise ValueError("Only SELECT queries are allowed.")

    pool = await get_pool(db_user, db_pass)
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *(params or []))
        return [dict(row) for row in rows]
