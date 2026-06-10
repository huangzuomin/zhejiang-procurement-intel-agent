from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Notice, OpportunityCard


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

    def upsert_notice(self, notice: Notice, *, fetch_run_id: str, seen_at: str) -> int:
        self.initialize()
        project_name = getattr(notice, "project_name", None)
        with self.connect() as conn:
            existing = conn.execute(
                "select id, first_seen_at from notices where detail_url = ?",
                (notice.url,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    update notices
                    set title = ?,
                        notice_type = ?,
                        source_column = ?,
                        source_column_path = ?,
                        source_category_code = ?,
                        publish_date = ?,
                        region = ?,
                        category_code = ?,
                        buyer = ?,
                        budget = ?,
                        deadline = ?,
                        project_name = ?,
                        last_seen_at = ?,
                        latest_fetch_run_id = ?
                    where id = ?
                    """,
                    (
                        notice.title,
                        notice.notice_type,
                        notice.source_column,
                        notice.source_column_path,
                        notice.source_category_code,
                        notice.publish_date,
                        notice.region,
                        notice.category_code,
                        notice.buyer,
                        notice.budget,
                        notice.deadline,
                        project_name,
                        seen_at,
                        fetch_run_id,
                        existing["id"],
                    ),
                )
                conn.commit()
                return int(existing["id"])

            cursor = conn.execute(
                """
                insert into notices (
                  detail_url,
                  title,
                  notice_type,
                  source_column,
                  source_column_path,
                  source_category_code,
                  publish_date,
                  region,
                  category_code,
                  buyer,
                  budget,
                  deadline,
                  project_name,
                  first_seen_at,
                  last_seen_at,
                  latest_fetch_run_id
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notice.url,
                    notice.title,
                    notice.notice_type,
                    notice.source_column,
                    notice.source_column_path,
                    notice.source_category_code,
                    notice.publish_date,
                    notice.region,
                    notice.category_code,
                    notice.buyer,
                    notice.budget,
                    notice.deadline,
                    project_name,
                    seen_at,
                    seen_at,
                    fetch_run_id,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def count_notices(self) -> int:
        self.initialize()
        with self.connect() as conn:
            return int(conn.execute("select count(*) from notices").fetchone()[0])

    def get_notice_by_url(self, url: str) -> dict | None:
        self.initialize()
        with self.connect() as conn:
            row = conn.execute("select * from notices where detail_url = ?", (url,)).fetchone()
            return dict(row) if row else None

    def known_urls_for_date(self, today: str) -> set[str]:
        self.initialize()
        with self.connect() as conn:
            return {
                str(row[0])
                for row in conn.execute(
                    "select detail_url from notices where publish_date = ? or substr(first_seen_at, 1, 10) = ?",
                    (today, today),
                )
            }

    def upsert_opportunity_card(
        self,
        notice_id: int,
        card: OpportunityCard,
        *,
        scored_at: str,
        scorer_version: str = "v1",
    ) -> None:
        self.initialize()
        with self.connect() as conn:
            conn.execute(
                """
                insert into opportunity_cards (
                  notice_id,
                  opportunity_class,
                  primary_category,
                  is_media_relevant,
                  confidence,
                  reasons_json,
                  risks_json,
                  missing_fields_json,
                  recommended_action,
                  scored_at,
                  scorer_version
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(notice_id) do update set
                  opportunity_class = excluded.opportunity_class,
                  primary_category = excluded.primary_category,
                  is_media_relevant = excluded.is_media_relevant,
                  confidence = excluded.confidence,
                  reasons_json = excluded.reasons_json,
                  risks_json = excluded.risks_json,
                  missing_fields_json = excluded.missing_fields_json,
                  recommended_action = excluded.recommended_action,
                  scored_at = excluded.scored_at,
                  scorer_version = excluded.scorer_version
                """,
                (
                    notice_id,
                    card.opportunity_class,
                    card.classification.primary_category,
                    1 if card.classification.is_media_relevant else 0,
                    _confidence_to_float(card.classification.confidence),
                    json.dumps(card.reasons, ensure_ascii=False),
                    json.dumps(card.risks, ensure_ascii=False),
                    json.dumps(card.missing_fields, ensure_ascii=False),
                    card.recommended_action,
                    scored_at,
                    scorer_version,
                ),
            )
            conn.commit()

    def list_opportunity_cards(self) -> list[dict]:
        self.initialize()
        with self.connect() as conn:
            rows = conn.execute("select * from opportunity_cards order by notice_id").fetchall()
            return [dict(row) for row in rows]


def _confidence_to_float(value: str) -> float:
    return {
        "high": 0.9,
        "medium": 0.6,
        "low": 0.3,
    }.get(value, 0.0)
