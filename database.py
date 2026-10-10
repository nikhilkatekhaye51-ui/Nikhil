"""Database helpers for CampusPulse.

All SQL uses "?" placeholders (parameterized queries), so user input is never
pasted directly into SQL text. This protects against SQL injection.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "campuspulse.db")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    course TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def connect(db_path):
    """Open a connection, save changes on success, and always close it."""
    folder = os.path.dirname(db_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path):
    """Create the feedback table if it does not exist yet."""
    with connect(db_path) as conn:
        conn.execute(SCHEMA)


def utc_now():
    """Current UTC time as text, e.g. '2026-10-10 14:05:00'."""
    return datetime.now(timezone.utc).strftime(TIME_FORMAT)


def add_feedback(db_path, student_name, course, rating, message):
    """Insert one feedback row and return its new id."""
    with connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO feedback (student_name, course, rating, message, "
            "created_at) VALUES (?, ?, ?, ?, ?)",
            (student_name, course, rating, message, utc_now()),
        )
        return cursor.lastrowid


def is_duplicate(db_path, student_name, course, message, seconds=30):
    """True if the same feedback was saved in the last few seconds."""
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime(
        TIME_FORMAT
    )
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM feedback WHERE student_name = ? AND course = ? "
            "AND message = ? AND created_at >= ? LIMIT 1",
            (student_name, course, message, cutoff),
        ).fetchone()
    return row is not None


def list_feedback(db_path, course=None, limit=None):
    """Return feedback as a list of dicts, newest first."""
    query = (
        "SELECT id, student_name, course, rating, message, created_at "
        "FROM feedback"
    )
    params = []
    if course:
        query += " WHERE course = ?"
        params.append(course)
    query += " ORDER BY created_at DESC, id DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    with connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_stats(db_path):
    """Calculate dashboard statistics from the real database records."""
    with connect(db_path) as conn:
        total, average, courses = conn.execute(
            "SELECT COUNT(*), AVG(rating), COUNT(DISTINCT course) FROM feedback"
        ).fetchone()
        course_rows = conn.execute(
            "SELECT course, COUNT(*) AS count, AVG(rating) AS average "
            "FROM feedback GROUP BY course ORDER BY average DESC, course"
        ).fetchall()
        dist_rows = conn.execute(
            "SELECT rating, COUNT(*) AS count FROM feedback GROUP BY rating"
        ).fetchall()

    distribution = {star: 0 for star in range(1, 6)}
    for row in dist_rows:
        distribution[row["rating"]] = row["count"]

    return {
        "total_feedback": total,
        "average_rating": round(average, 2) if average is not None else 0.0,
        "courses_with_feedback": courses,
        "rating_distribution": distribution,
        "courses": [
            {
                "course": row["course"],
                "count": row["count"],
                "average_rating": round(row["average"], 2),
            }
            for row in course_rows
        ],
    }
