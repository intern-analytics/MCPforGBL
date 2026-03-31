import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "brand_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "password")
    )

def run_query(sql: str, params=None):
    # Enforce read-only constraint
    upper_sql = sql.upper()
    forbidden_keywords = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE "]
    if any(keyword in upper_sql for keyword in forbidden_keywords):
        raise ValueError("Only SELECT queries are allowed.")

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description is not None:
                return cur.fetchall()
            return []
    finally:
        conn.close()
