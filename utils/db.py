"""SQLite data access layer for IP3.

All tables follow the schema defined in the product requirements (section 31).
The database file lives at ``data/ip3.db`` by default.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "ip3.db"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row access by column name."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "exports").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    memo TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS review_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    title TEXT,
    description TEXT,
    keywords TEXT,
    exclude_keywords TEXT,
    search_scope TEXT,
    top_n INTEGER,
    idea_structure TEXT,
    status TEXT,
    is_temporary INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS patents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT,
    application_no TEXT,
    publication_no TEXT,
    registration_no TEXT,
    title TEXT,
    applicant TEXT,
    inventor TEXT,
    abstract TEXT,
    filing_date TEXT,
    publication_date TEXT,
    registration_date TEXT,
    legal_status TEXT,
    ipc TEXT,
    cpc TEXT,
    representative_drawing_url TEXT,
    source_url TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS case_patents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_case_id INTEGER,
    patent_id INTEGER,
    rank INTEGER,
    similarity_score REAL,
    is_interested INTEGER DEFAULT 0,
    interest_status TEXT,
    is_excluded INTEGER DEFAULT 0,
    memo TEXT,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (review_case_id) REFERENCES review_cases(id) ON DELETE CASCADE,
    FOREIGN KEY (patent_id) REFERENCES patents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS patent_details_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patent_id INTEGER UNIQUE,
    claims_text TEXT,
    bibliographic_json TEXT,
    drawing_meta_json TEXT,
    last_fetched_at TEXT,
    FOREIGN KEY (patent_id) REFERENCES patents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS comparison_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_case_id INTEGER,
    selected_patent_ids_json TEXT,
    status TEXT,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (review_case_id) REFERENCES review_cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS comparison_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comparison_run_id INTEGER,
    review_case_id INTEGER,
    patent_id INTEGER,
    similar_points TEXT,
    different_points TEXT,
    check_points TEXT,
    source_locations TEXT,
    original_evidence TEXT,
    judgment_status TEXT,
    summary_memo TEXT,
    created_at TEXT,
    FOREIGN KEY (comparison_run_id) REFERENCES comparison_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_case_id INTEGER,
    comparison_run_id INTEGER,
    report_type TEXT,
    file_path TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE,
    value TEXT,
    updated_at TEXT
);
"""


def init_db() -> None:
    """Create all tables if they do not yet exist."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def query_all(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_one(sql: str, params: Iterable[Any] = ()) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(sql, tuple(params)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    """Run an INSERT/UPDATE/DELETE and return lastrowid."""
    conn = get_connection()
    try:
        cur = conn.execute(sql, tuple(params))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def create_project(name: str, description: str = "") -> int:
    ts = _now()
    return execute(
        "INSERT INTO projects (name, description, created_at, updated_at) VALUES (?,?,?,?)",
        (name, description, ts, ts),
    )


def list_projects() -> list[dict]:
    return query_all("SELECT * FROM projects ORDER BY updated_at DESC")


def get_project(project_id: int) -> dict | None:
    return query_one("SELECT * FROM projects WHERE id=?", (project_id,))


def update_project(project_id: int, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k}=?" for k in fields)
    execute(f"UPDATE projects SET {cols} WHERE id=?", (*fields.values(), project_id))


def delete_project(project_id: int) -> None:
    # Detach review cases (project becomes "미지정") rather than deleting them.
    execute("UPDATE review_cases SET project_id=NULL WHERE project_id=?", (project_id,))
    execute("DELETE FROM projects WHERE id=?", (project_id,))


# ---------------------------------------------------------------------------
# Review cases
# ---------------------------------------------------------------------------
def create_review_case(
    title: str,
    description: str,
    keywords: str,
    exclude_keywords: str,
    search_scope: str,
    top_n: int,
    project_id: int | None = None,
    idea_structure: dict | None = None,
    status: str = "임시저장",
    is_temporary: int = 1,
) -> int:
    ts = _now()
    return execute(
        """INSERT INTO review_cases
        (project_id, title, description, keywords, exclude_keywords, search_scope,
         top_n, idea_structure, status, is_temporary, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            project_id,
            title,
            description,
            keywords,
            exclude_keywords,
            search_scope,
            top_n,
            json.dumps(idea_structure or {}, ensure_ascii=False),
            status,
            is_temporary,
            ts,
            ts,
        ),
    )


def get_review_case(case_id: int) -> dict | None:
    row = query_one("SELECT * FROM review_cases WHERE id=?", (case_id,))
    if row and row.get("idea_structure"):
        try:
            row["idea_structure"] = json.loads(row["idea_structure"])
        except (json.JSONDecodeError, TypeError):
            row["idea_structure"] = {}
    return row


def list_review_cases(include_temporary: bool = True) -> list[dict]:
    if include_temporary:
        return query_all("SELECT * FROM review_cases ORDER BY updated_at DESC")
    return query_all(
        "SELECT * FROM review_cases WHERE is_temporary=0 ORDER BY updated_at DESC"
    )


def list_temporary_cases() -> list[dict]:
    return query_all(
        "SELECT * FROM review_cases WHERE is_temporary=1 ORDER BY updated_at DESC"
    )


def update_review_case(case_id: int, **fields) -> None:
    if not fields:
        return
    if "idea_structure" in fields and isinstance(fields["idea_structure"], (dict, list)):
        fields["idea_structure"] = json.dumps(fields["idea_structure"], ensure_ascii=False)
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k}=?" for k in fields)
    execute(f"UPDATE review_cases SET {cols} WHERE id=?", (*fields.values(), case_id))


def confirm_save_case(case_id: int) -> None:
    """Promote a temporary case to a confirmed (saved) review case."""
    update_review_case(case_id, is_temporary=0, status="저장됨")


def delete_review_case(case_id: int) -> None:
    execute("DELETE FROM review_cases WHERE id=?", (case_id,))


# ---------------------------------------------------------------------------
# Patents
# ---------------------------------------------------------------------------
def upsert_patent(patent: dict) -> int:
    """Insert a patent or return the id of an existing one (matched by number)."""
    pub = patent.get("publication_no") or ""
    app = patent.get("application_no") or ""
    existing = None
    if pub:
        existing = query_one("SELECT id FROM patents WHERE publication_no=?", (pub,))
    if not existing and app:
        existing = query_one("SELECT id FROM patents WHERE application_no=?", (app,))
    ts = _now()
    if existing:
        return existing["id"]
    return execute(
        """INSERT INTO patents
        (country, application_no, publication_no, registration_no, title, applicant,
         inventor, abstract, filing_date, publication_date, registration_date,
         legal_status, ipc, cpc, representative_drawing_url, source_url,
         created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            patent.get("country", ""),
            app,
            pub,
            patent.get("registration_no", ""),
            patent.get("title", ""),
            patent.get("applicant", ""),
            patent.get("inventor", ""),
            patent.get("abstract", ""),
            patent.get("filing_date", ""),
            patent.get("publication_date", ""),
            patent.get("registration_date", ""),
            patent.get("legal_status", ""),
            patent.get("ipc", ""),
            patent.get("cpc", ""),
            patent.get("representative_drawing_url", ""),
            patent.get("source_url", ""),
            ts,
            ts,
        ),
    )


def get_patent(patent_id: int) -> dict | None:
    return query_one("SELECT * FROM patents WHERE id=?", (patent_id,))


# ---------------------------------------------------------------------------
# Case <-> patent links
# ---------------------------------------------------------------------------
def link_case_patent(
    review_case_id: int,
    patent_id: int,
    rank: int,
    similarity_score: float,
) -> int:
    existing = query_one(
        "SELECT id FROM case_patents WHERE review_case_id=? AND patent_id=?",
        (review_case_id, patent_id),
    )
    if existing:
        return existing["id"]
    ts = _now()
    return execute(
        """INSERT INTO case_patents
        (review_case_id, patent_id, rank, similarity_score, is_interested,
         interest_status, is_excluded, memo, created_at, updated_at)
        VALUES (?,?,?,?,0,'',0,'',?,?)""",
        (review_case_id, patent_id, rank, similarity_score, ts, ts),
    )


def get_case_patents(review_case_id: int) -> list[dict]:
    """Return joined patent + case_patent rows for a review case, ranked."""
    return query_all(
        """SELECT p.*, cp.id AS link_id, cp.rank, cp.similarity_score,
                  cp.is_interested, cp.interest_status, cp.is_excluded, cp.memo
           FROM case_patents cp
           JOIN patents p ON p.id = cp.patent_id
           WHERE cp.review_case_id=?
           ORDER BY cp.rank ASC""",
        (review_case_id,),
    )


def get_case_patent(review_case_id: int, patent_id: int) -> dict | None:
    return query_one(
        """SELECT p.*, cp.id AS link_id, cp.rank, cp.similarity_score,
                  cp.is_interested, cp.interest_status, cp.is_excluded, cp.memo
           FROM case_patents cp
           JOIN patents p ON p.id = cp.patent_id
           WHERE cp.review_case_id=? AND cp.patent_id=?""",
        (review_case_id, patent_id),
    )


def update_case_patent(link_id: int, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k}=?" for k in fields)
    execute(f"UPDATE case_patents SET {cols} WHERE id=?", (*fields.values(), link_id))


def delete_case_patents(review_case_id: int) -> None:
    """Remove all patent links for a case (used before a re-search)."""
    execute("DELETE FROM case_patents WHERE review_case_id=?", (review_case_id,))


def list_library_patents() -> list[dict]:
    """All interested patents across every case (the boorkmark library)."""
    return query_all(
        """SELECT p.*, cp.id AS link_id, cp.review_case_id, cp.similarity_score,
                  cp.interest_status, cp.memo, cp.is_interested,
                  rc.title AS case_title, rc.project_id,
                  pr.name AS project_name
           FROM case_patents cp
           JOIN patents p ON p.id = cp.patent_id
           JOIN review_cases rc ON rc.id = cp.review_case_id
           LEFT JOIN projects pr ON pr.id = rc.project_id
           WHERE cp.is_interested=1
           ORDER BY cp.updated_at DESC"""
    )


# ---------------------------------------------------------------------------
# Detail cache
# ---------------------------------------------------------------------------
def save_patent_details(
    patent_id: int,
    claims_text: str = "",
    bibliographic: dict | None = None,
    drawing_meta: dict | None = None,
) -> None:
    existing = query_one(
        "SELECT id FROM patent_details_cache WHERE patent_id=?", (patent_id,)
    )
    ts = _now()
    bib = json.dumps(bibliographic or {}, ensure_ascii=False)
    draw = json.dumps(drawing_meta or {}, ensure_ascii=False)
    if existing:
        execute(
            """UPDATE patent_details_cache
               SET claims_text=?, bibliographic_json=?, drawing_meta_json=?, last_fetched_at=?
               WHERE patent_id=?""",
            (claims_text, bib, draw, ts, patent_id),
        )
    else:
        execute(
            """INSERT INTO patent_details_cache
               (patent_id, claims_text, bibliographic_json, drawing_meta_json, last_fetched_at)
               VALUES (?,?,?,?,?)""",
            (patent_id, claims_text, bib, draw, ts),
        )


def get_patent_details(patent_id: int) -> dict | None:
    row = query_one(
        "SELECT * FROM patent_details_cache WHERE patent_id=?", (patent_id,)
    )
    if not row:
        return None
    for key in ("bibliographic_json", "drawing_meta_json"):
        if row.get(key):
            try:
                row[key.replace("_json", "")] = json.loads(row[key])
            except (json.JSONDecodeError, TypeError):
                row[key.replace("_json", "")] = {}
    return row


# ---------------------------------------------------------------------------
# Comparison runs / results
# ---------------------------------------------------------------------------
def create_comparison_run(review_case_id: int, selected_patent_ids: list[int]) -> int:
    ts = _now()
    return execute(
        """INSERT INTO comparison_runs
           (review_case_id, selected_patent_ids_json, status, created_at, updated_at)
           VALUES (?,?,?,?,?)""",
        (review_case_id, json.dumps(selected_patent_ids), "완료", ts, ts),
    )


def save_comparison_result(run_id: int, review_case_id: int, result: dict) -> int:
    ts = _now()
    return execute(
        """INSERT INTO comparison_results
           (comparison_run_id, review_case_id, patent_id, similar_points,
            different_points, check_points, source_locations, original_evidence,
            judgment_status, summary_memo, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            run_id,
            review_case_id,
            result["patent_id"],
            json.dumps(result.get("similar_points", []), ensure_ascii=False),
            json.dumps(result.get("different_points", []), ensure_ascii=False),
            json.dumps(result.get("check_points", []), ensure_ascii=False),
            json.dumps(result.get("source_locations", []), ensure_ascii=False),
            json.dumps(result.get("original_evidence", []), ensure_ascii=False),
            result.get("judgment_status", "확인필요"),
            result.get("summary_memo", ""),
            ts,
        ),
    )


def get_latest_comparison_run(review_case_id: int) -> dict | None:
    return query_one(
        "SELECT * FROM comparison_runs WHERE review_case_id=? ORDER BY id DESC LIMIT 1",
        (review_case_id,),
    )


def get_comparison_results(run_id: int) -> list[dict]:
    rows = query_all(
        """SELECT cr.*, p.title, p.country, p.applicant, p.application_no, p.publication_no
           FROM comparison_results cr
           JOIN patents p ON p.id = cr.patent_id
           WHERE cr.comparison_run_id=?
           ORDER BY cr.id ASC""",
        (run_id,),
    )
    for r in rows:
        for key in (
            "similar_points",
            "different_points",
            "check_points",
            "source_locations",
            "original_evidence",
        ):
            try:
                r[key] = json.loads(r[key]) if r.get(key) else []
            except (json.JSONDecodeError, TypeError):
                r[key] = []
    return rows


def update_comparison_memo(result_id: int, memo: str) -> None:
    execute("UPDATE comparison_results SET summary_memo=? WHERE id=?", (memo, result_id))


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def record_report(
    review_case_id: int,
    comparison_run_id: int | None,
    report_type: str,
    file_path: str,
) -> int:
    return execute(
        """INSERT INTO reports
           (review_case_id, comparison_run_id, report_type, file_path, created_at)
           VALUES (?,?,?,?,?)""",
        (review_case_id, comparison_run_id, report_type, file_path, _now()),
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def set_setting(key: str, value: str) -> None:
    existing = query_one("SELECT id FROM settings WHERE key=?", (key,))
    ts = _now()
    if existing:
        execute("UPDATE settings SET value=?, updated_at=? WHERE key=?", (value, ts, key))
    else:
        execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?,?,?)", (key, value, ts)
        )


def get_setting(key: str, default: str = "") -> str:
    row = query_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row and row["value"] is not None else default


def all_settings() -> dict:
    return {r["key"]: r["value"] for r in query_all("SELECT key, value FROM settings")}


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------
def count_rows(table: str) -> int:
    row = query_one(f"SELECT COUNT(*) AS c FROM {table}")
    return row["c"] if row else 0


def clear_cache() -> int:
    """Clear cached patent details. Returns rows removed."""
    n = count_rows("patent_details_cache")
    execute("DELETE FROM patent_details_cache")
    return n


def delete_temporary_cases() -> int:
    n = len(list_temporary_cases())
    execute("DELETE FROM review_cases WHERE is_temporary=1")
    return n
