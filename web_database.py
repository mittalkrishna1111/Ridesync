"""Web-safe database connection helpers reusing database.py without modifying it."""

from contextlib import contextmanager
from threading import Lock
import mysql.connector as mysql_c
from mysql.connector import pooling

import database

_POOL = None
_POOL_LOCK = Lock()


def _get_pool():
    """Lazily create a MySQL connection pool using database.py's cached password."""
    global _POOL
    if _POOL is not None:
        return _POOL

    if database.MYSQL_PASSWORD is None:
        return None

    with _POOL_LOCK:
        if _POOL is None:
            _POOL = pooling.MySQLConnectionPool(
                pool_name="ridesync_web_pool",
                pool_size=6,
                pool_reset_session=True,
                host=database.HOST,
                user=database.USER,
                password=database.MYSQL_PASSWORD,
                database=database.DATABASE,
            )
    return _POOL


def open_db_connection():
    """Open a fresh MySQL connection (from pool if initialized, else database.get_connection)."""
    pool = _get_pool()
    if pool is not None:
        try:
            return pool.get_connection()
        except mysql_c.Error:
            pass
    return database.get_connection()


@contextmanager
def db_cursor(dictionary=False):
    """Yield (connection, cursor) and guarantee clean rollback, cursor, and connection cleanup."""
    conn = open_db_connection()
    if conn is None:
        raise ConnectionError("Unable to connect to the RideSync database.")

    cursor = None
    try:
        cursor = conn.cursor(dictionary=dictionary)
        yield conn, cursor
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            if conn.in_transaction:
                conn.rollback()
            conn.close()


def is_mysql_error(exc):
    """Return True if exc is a mysql.connector.Error."""
    return isinstance(exc, mysql_c.Error)
