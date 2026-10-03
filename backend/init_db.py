from database.db import get_db_connection
import os

def init_db():
    conn = get_db_connection()
    schema_path = os.path.join(os.path.dirname(__file__), "database", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    conn.commit()
    conn.close()

    print("✅ Database initialized successfully")

if __name__ == "__main__":
    init_db()