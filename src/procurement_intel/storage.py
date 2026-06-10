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

    def upsert_notice(
        self,
        notice: Notice,
        *,
        fetch_run_id: str,
        seen_at: str,
        preserve_existing_fields: bool = False,
    ) -> int:
        self.initialize()
        project_name = getattr(notice, "project_name", None)
        with self.connect() as conn:
            existing = conn.execute(
                "select * from notices where detail_url = ?",
                (notice.url,),
            ).fetchone()
            if existing:
                buyer = _preserve_if_missing(notice.buyer, existing["buyer"], preserve_existing_fields)
                budget = _preserve_if_missing(notice.budget, existing["budget"], preserve_existing_fields)
                deadline = _preserve_if_missing(notice.deadline, existing["deadline"], preserve_existing_fields)
                project_name = _preserve_if_missing(project_name, existing["project_name"], preserve_existing_fields)
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
                        buyer,
                        budget,
                        deadline,
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

    def get_opportunity_card_by_notice_id(self, notice_id: int) -> dict | None:
        self.initialize()
        with self.connect() as conn:
            row = conn.execute("select * from opportunity_cards where notice_id = ?", (notice_id,)).fetchone()
            return dict(row) if row else None

    def record_fetch_run(
        self,
        *,
        run_id: str,
        run_type: str,
        started_at: str,
        finished_at: str,
        source: str | None,
        raw_count: int,
        new_count: int,
        enriched_count: int,
        status: str,
        error: str | None = None,
    ) -> None:
        self.initialize()
        with self.connect() as conn:
            conn.execute(
                """
                insert into fetch_runs (
                  run_id,
                  run_type,
                  started_at,
                  finished_at,
                  source,
                  raw_count,
                  new_count,
                  enriched_count,
                  status,
                  error
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(run_id) do update set
                  run_type = excluded.run_type,
                  started_at = excluded.started_at,
                  finished_at = excluded.finished_at,
                  source = excluded.source,
                  raw_count = excluded.raw_count,
                  new_count = excluded.new_count,
                  enriched_count = excluded.enriched_count,
                  status = excluded.status,
                  error = excluded.error
                """,
                (
                    run_id,
                    run_type,
                    started_at,
                    finished_at,
                    source,
                    raw_count,
                    new_count,
                    enriched_count,
                    status,
                    error,
                ),
            )
            conn.commit()

    def record_quality_report(self, *, fetch_run_id: str, report_json: str, created_at: str) -> None:
        self.initialize()
        with self.connect() as conn:
            conn.execute(
                """
                insert into quality_reports (fetch_run_id, report_json, created_at)
                values (?, ?, ?)
                """,
                (fetch_run_id, report_json, created_at),
            )
            conn.commit()

    def record_push_event(
        self,
        *,
        notice_id: int | None,
        brief_date: str,
        brief_mode: str,
        status: str,
        pushed_at: str,
    ) -> None:
        self.initialize()
        with self.connect() as conn:
            conn.execute(
                """
                insert into push_events (notice_id, brief_date, brief_mode, pushed_at, status)
                values (?, ?, ?, ?, ?)
                """,
                (notice_id, brief_date, brief_mode, pushed_at, status),
            )
            conn.commit()

    def list_cards_for_date(self, today: str) -> list[dict]:
        self.initialize()
        with self.connect() as conn:
            rows = conn.execute(
                """
                select
                  notices.id as notice_id,
                  notices.detail_url,
                  notices.title,
                  notices.notice_type,
                  notices.source_column,
                  notices.publish_date,
                  notices.region,
                  notices.buyer,
                  notices.budget,
                  notices.deadline,
                  opportunity_cards.opportunity_class,
                  opportunity_cards.primary_category,
                  opportunity_cards.reasons_json,
                  opportunity_cards.risks_json,
                  opportunity_cards.missing_fields_json,
                  opportunity_cards.recommended_action,
                  opportunity_cards.scored_at
                from notices
                join opportunity_cards on opportunity_cards.notice_id = notices.id
                where notices.publish_date = ?
                   or (notices.publish_date is null and substr(notices.first_seen_at, 1, 10) = ?)
                order by
                  case opportunity_cards.opportunity_class
                    when 'A' then 1
                    when 'B' then 2
                    when 'C' then 3
                    else 4
                  end,
                  notices.publish_date desc,
                  notices.id
                """,
                (today, today),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_unpushed_focus_cards(self, today: str, *, pushed_mode: str = "am") -> list[dict]:
        self.initialize()
        with self.connect() as conn:
            rows = conn.execute(
                """
                select
                  notices.id as notice_id,
                  notices.detail_url,
                  notices.title,
                  notices.notice_type,
                  notices.source_column,
                  notices.publish_date,
                  notices.region,
                  notices.buyer,
                  notices.budget,
                  notices.deadline,
                  opportunity_cards.opportunity_class,
                  opportunity_cards.primary_category,
                  opportunity_cards.reasons_json,
                  opportunity_cards.risks_json,
                  opportunity_cards.missing_fields_json,
                  opportunity_cards.recommended_action,
                  opportunity_cards.scored_at
                from notices
                join opportunity_cards on opportunity_cards.notice_id = notices.id
                where (notices.publish_date = ? or (notices.publish_date is null and substr(notices.first_seen_at, 1, 10) = ?))
                  and opportunity_cards.opportunity_class in ('A', 'B')
                  and not exists (
                    select 1
                    from push_events
                    where push_events.notice_id = notices.id
                      and push_events.brief_date = ?
                      and push_events.brief_mode = ?
                      and push_events.status = 'success'
                  )
                order by
                  case opportunity_cards.opportunity_class when 'A' then 1 else 2 end,
                  notices.id
                """,
                (today, today, today, pushed_mode),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_fetch_runs_for_date(self, today: str, *, run_type: str | None = None) -> list[dict]:
        self.initialize()
        query = """
            select *
            from fetch_runs
            where substr(started_at, 1, 10) = ?
        """
        params: list[str] = [today]
        if run_type:
            query += " and run_type = ?"
            params.append(run_type)
        query += " order by started_at, id"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]


def _confidence_to_float(value: str) -> float:
    return {
        "high": 0.9,
        "medium": 0.6,
        "low": 0.3,
    }.get(value, 0.0)


def _preserve_if_missing(value, existing, preserve: bool):
    if preserve and value is None and existing is not None:
        return existing
    return value
