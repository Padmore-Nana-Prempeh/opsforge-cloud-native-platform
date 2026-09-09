import os

import psycopg

from app.common.config import DATABASE_URL


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost/opsforge",
)


def get_connection():
    return psycopg.connect(DATABASE_URL)

def database_is_ready() -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        return True

    except psycopg.Error:
        return False


def create_order(item_id: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO orders (item_id, status)
                VALUES (%s, %s)
                RETURNING id, item_id, status, created_at
                """,
                (item_id, "created"),
            )

            row = cur.fetchone()

    return {
        "id": row[0],
        "item_id": row[1],
        "status": row[2],
        "created_at": row[3].isoformat(),
    }


def get_order(order_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, item_id, status, created_at
                FROM orders
                WHERE id = %s
                """,
                (order_id,),
            )

            row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "item_id": row[1],
        "status": row[2],
        "created_at": row[3].isoformat(),
    }


def update_order_status(order_id: int, status: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE orders
                SET status = %s
                WHERE id = %s
                RETURNING id, item_id, status, created_at
                """,
                (status, order_id),
            )

            row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "item_id": row[1],
        "status": row[2],
        "created_at": row[3].isoformat(),
    }
