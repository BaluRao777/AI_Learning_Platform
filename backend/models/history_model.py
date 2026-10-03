import json
from database.db import get_db_connection


def get_existing(topic, level, mode, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM history 
        WHERE topic=? AND level=? AND mode=? AND user_id=?
    """, (topic, level, mode, user_id))

    data = cursor.fetchone()
    conn.close()

    return data


def save_history(user_id, topic, level, mode, subtopics, explanation, images):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO history (user_id, topic, level, mode, subtopics, explanations, images)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        topic,
        level,
        mode,
        json.dumps(subtopics),
        explanation,
        json.dumps(images)
    ))

    conn.commit()
    conn.close()


def list_history(user_id, limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, topic, level, mode, subtopics, explanations, images, created_at
        FROM history
        WHERE user_id=?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "topic": row["topic"],
                "level": row["level"],
                "mode": row["mode"],
                "subtopics": json.loads(row["subtopics"] or "[]"),
                "images": json.loads(row["images"] or "[]"),
                "explanation": row["explanations"] or "",
                "timestamp": row["created_at"],
            }
        )
    return result