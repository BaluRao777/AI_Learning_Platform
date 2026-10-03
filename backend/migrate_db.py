from database.db import get_db_connection


def migrate():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(history)")
    history_columns = {row[1] for row in cursor.fetchall()}

    if "explanations" not in history_columns and "explanation" in history_columns:
        cursor.execute("ALTER TABLE history RENAME COLUMN explanation TO explanations")
        print("Migrated: history.explanation -> history.explanations")

    if "subtopics" not in history_columns and "prompts" in history_columns:
        cursor.execute("ALTER TABLE history RENAME COLUMN prompts TO subtopics")
        print("Migrated: history.prompts -> history.subtopics")

    if "mode" not in history_columns:
        cursor.execute("ALTER TABLE history ADD COLUMN mode TEXT DEFAULT 'learn'")
        print("Migrated: added history.mode")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_user_created ON history(user_id, created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_topic ON history(topic)")
    conn.commit()
    conn.close()
    print("Database migration complete")


if __name__ == "__main__":
    migrate()
