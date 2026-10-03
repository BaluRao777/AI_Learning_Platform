CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL CHECK(length(email) > 3),
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    level TEXT NOT NULL CHECK(level IN ('school', 'college')),
    mode TEXT NOT NULL CHECK(mode IN ('learn', 'exam')),
    subtopics TEXT NOT NULL,
    explanations TEXT NOT NULL,
    images TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_history_user_created ON history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_topic ON history(topic);