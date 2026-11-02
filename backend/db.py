import os
import sqlite3
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("INVERTER_DB", os.path.join(HERE, "inverter.db"))


def init_db():
    with open(os.path.join(HERE, "schema.sql")) as f:
        schema = f.read()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.close()


@contextmanager
def transaction():
    """One transaction per request. BEGIN IMMEDIATE takes the write lock up front,
    so two requests can never interleave and push the load past the limit."""
    conn = sqlite3.connect(DB_PATH, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
