import aiosqlite
from datetime import datetime
from .models import SCHEMA_SQL

DB_PATH = "app/db/bot.sqlite3"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA_SQL)

        # --- Safe migrations: eski DB bo'lsa ham buzmaydi ---
        for sql in [
            "ALTER TABLE users ADD COLUMN phone TEXT",
            "ALTER TABLE users ADD COLUMN car_plate TEXT",
        ]:
            try:
                await db.execute(sql)
            except Exception:
                # column allaqachon bor bo'lsa xato beradi — ignor qilamiz
                pass

        await db.commit()


async def upsert_user(
    telegram_id: int,
    first_name: str,
    last_name: str,
    phone: str,
    car_plate: str,
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (telegram_id, first_name, last_name, phone, car_plate, registered_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                phone=excluded.phone,
                car_plate=excluded.car_plate
            """,
            (
                telegram_id,
                first_name.strip(),
                last_name.strip(),
                phone.strip(),
                car_plate.strip(),
                now,
            ),
        )
        await db.commit()


async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT telegram_id, first_name, last_name, phone, car_plate
            FROM users
            WHERE telegram_id=?
            """,
            (telegram_id,),
        )
        return await cur.fetchone()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT telegram_id, first_name, last_name, phone, car_plate FROM users"
        )
        return await cur.fetchall()


async def ensure_daily_row(telegram_id: int, date: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO daily_submissions (telegram_id, date, status)
            VALUES (?, ?, 'PENDING')
            """,
            (telegram_id, date),
        )
        await db.commit()


async def save_reason(telegram_id: int, date: str, reason: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO daily_submissions (telegram_id, date, status)
            VALUES (?, ?, 'PENDING')
            """,
            (telegram_id, date),
        )

        await db.execute(
            """
            UPDATE daily_submissions
            SET reason=?, status='NOT_SUBMITTED'
            WHERE telegram_id=? AND date=?
            """,
            (reason.strip(), telegram_id, date),
        )
        await db.commit()


async def add_video(
    telegram_id: int,
    date: str,
    kindergarten_no: str,
    file_id: str,
    sheet_row: int | None = None,   # ✅ Sheets qatori raqami
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO daily_submissions (telegram_id, date, status)
            VALUES (?, ?, 'PENDING')
            """,
            (telegram_id, date),
        )

        await db.execute(
            """
            INSERT INTO videos (telegram_id, date, kindergarten_no, video_file_id, sheet_row, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (telegram_id, date, kindergarten_no.strip(), file_id, sheet_row, now),
        )

        await db.execute(
            """
            UPDATE daily_submissions
            SET status='SUBMITTED', reason=NULL
            WHERE telegram_id=? AND date=?
            """,
            (telegram_id, date),
        )

        await db.commit()


async def count_videos_for_user_date(telegram_id: int, date: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(1) FROM videos WHERE telegram_id=? AND date=?",
            (telegram_id, date),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def get_daily_reason_and_status(telegram_id: int, date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO daily_submissions (telegram_id, date, status)
            VALUES (?, ?, 'PENDING')
            """,
            (telegram_id, date),
        )
        cur = await db.execute(
            "SELECT status, reason FROM daily_submissions WHERE telegram_id=? AND date=?",
            (telegram_id, date),
        )
        return await cur.fetchone()


async def get_report_rows_for_date(date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT
                u.first_name,
                u.last_name,
                COALESCE(v.cnt, 0) AS video_count,
                d.status,
                d.reason
            FROM users u
            LEFT JOIN (
                SELECT telegram_id, date, COUNT(1) AS cnt
                FROM videos
                WHERE date=?
                GROUP BY telegram_id, date
            ) v ON v.telegram_id = u.telegram_id
            LEFT JOIN daily_submissions d
                ON d.telegram_id = u.telegram_id AND d.date=?
            ORDER BY u.last_name, u.first_name
            """,
            (date, date),
        )
        return await cur.fetchall()


async def get_last_video_sheet_row(telegram_id: int, date: str) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT sheet_row
            FROM videos
            WHERE telegram_id=? AND date=? AND sheet_row IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (telegram_id, date),
        )
        row = await cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
