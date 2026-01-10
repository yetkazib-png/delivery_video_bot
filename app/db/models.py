SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    car_plate TEXT,
    registered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_submissions (
    telegram_id INTEGER NOT NULL,
    date TEXT NOT NULL, -- YYYY-MM-DD
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    UNIQUE(telegram_id, date),
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    date TEXT NOT NULL, -- YYYY-MM-DD
    kindergarten_no TEXT NOT NULL,
    video_file_id TEXT NOT NULL,
    sheet_row INTEGER,              -- ✅ Google Sheets qator raqami (1-based)
    submitted_at TEXT NOT NULL,
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
);

CREATE INDEX IF NOT EXISTS idx_videos_user_date
ON videos(telegram_id, date);
"""
