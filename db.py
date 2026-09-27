import sqlite3
from contextlib import contextmanager

from werkzeug.security import generate_password_hash

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    incoming_number TEXT NOT NULL,
    saved_date TEXT NOT NULL,
    file_path TEXT NOT NULL,
    archive_filename TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    config.ensure_dirs()
    with get_db() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("Admin",)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("Admin", generate_password_hash("Admin"), "admin"),
            )


def get_user_by_username(username: str):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def get_user_by_id(user_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def create_user(username: str, password: str, role: str = "user"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), role),
        )


def add_scan(title: str, incoming_number: str, saved_date: str, file_path: str,
             archive_filename: str, created_by: str):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO scans (title, incoming_number, saved_date, file_path, "
            "archive_filename, created_by) VALUES (?, ?, ?, ?, ?, ?)",
            (title, incoming_number, saved_date, file_path, archive_filename, created_by),
        )
        return cur.lastrowid


def list_scans():
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM scans ORDER BY id DESC"
        ).fetchall()


def get_scan(scan_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM scans WHERE id = ?", (scan_id,)
        ).fetchone()
