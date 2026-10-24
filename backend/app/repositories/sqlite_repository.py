import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SqliteRepository:
    def __init__(self, database_path: str):
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS ticket_summaries (
                    thread_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS customer_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_key TEXT NOT NULL,
                    fact_key TEXT NOT NULL,
                    fact_value TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    confirmed INTEGER NOT NULL DEFAULT 0,
                    expires_at TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ingestion_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL,
                    imported_messages INTEGER NOT NULL,
                    imported_threads INTEGER NOT NULL,
                    indexed_cases INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def save_summary(self, thread_id: str, summary: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO ticket_summaries(thread_id, summary, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET summary=excluded.summary, updated_at=excluded.updated_at
                """,
                (thread_id, json.dumps(summary, ensure_ascii=False), now),
            )

    def get_summary(self, thread_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT summary FROM ticket_summaries WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        return json.loads(row["summary"]) if row else None

    def save_ingestion_run(self, source_path: str, imported_messages: int, imported_threads: int, indexed_cases: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO ingestion_runs(source_path, imported_messages, imported_threads, indexed_cases, created_at) VALUES (?, ?, ?, ?, ?)",
                (source_path, imported_messages, imported_threads, indexed_cases, datetime.now(timezone.utc).isoformat()),
            )
