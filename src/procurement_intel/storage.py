from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_STATEMENTS = (
    """
    create table if not exists fetch_runs (
      id integer primary key autoincrement,
      run_id text not null unique,
      run_type text not null,
      started_at text not null,
      finished_at text,
      source text,
      raw_count integer not null default 0,
      new_count integer not null default 0,
      enriched_count integer not null default 0,
      status text not null default 'running',
      error text
    )
    """,
    """
    create table if not exists notices (
      id integer primary key autoincrement,
      detail_url text not null unique,
      title text not null,
      notice_type text,
      source_column text,
      source_column_path text,
      source_category_code text,
      publish_date text,
      region text,
      category_code text,
      buyer text,
      budget real,
      deadline text,
      project_name text,
      first_seen_at text not null,
      last_seen_at text not null,
      latest_fetch_run_id text
    )
    """,
    """
    create table if not exists notice_details (
      notice_id integer primary key,
      raw_detail_text text,
      contact text,
      phone text,
      detail_enriched_at text,
      parser_version text not null,
      foreign key(notice_id) references notices(id)
    )
    """,
    """
    create table if not exists opportunity_cards (
      notice_id integer primary key,
      opportunity_class text not null,
      primary_category text,
      is_media_relevant integer not null,
      confidence real,
      reasons_json text not null,
      risks_json text not null,
      missing_fields_json text not null,
      recommended_action text,
      scored_at text not null,
      scorer_version text not null,
      foreign key(notice_id) references notices(id)
    )
    """,
    """
    create table if not exists push_events (
      id integer primary key autoincrement,
      notice_id integer,
      brief_date text not null,
      brief_mode text not null,
      pushed_at text not null,
      status text not null,
      foreign key(notice_id) references notices(id)
    )
    """,
    """
    create table if not exists quality_reports (
      id integer primary key autoincrement,
      fetch_run_id text not null,
      report_json text not null,
      created_at text not null
    )
    """,
)


class SQLiteStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("pragma foreign_keys = on")
            for statement in SCHEMA_STATEMENTS:
                conn.execute(statement)
            conn.commit()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("pragma foreign_keys = on")
        return conn
