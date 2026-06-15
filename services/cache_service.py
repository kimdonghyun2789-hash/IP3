"""Caching + persistence orchestration for IP3.

Implements the "light cache" principle from the product requirements:

* search runs fetch only the list-level fields and store them
* claims / bibliography / drawing metadata are cached on first access
* drawing image binaries and full raw JSON are never stored

SQLite holds text + metadata only.
"""
from __future__ import annotations

from services import kiprisplus_client
from utils import config, db


def run_search(case_id: int, case: dict) -> tuple[int, str]:
    """Execute a search for a review case and persist the results.

    Returns ``(result_count, source)`` where source is 'kiprisplus' or 'sample'.
    """
    keywords = [k.strip() for k in (case.get("keywords") or "").split(",") if k.strip()]
    excludes = [
        e.strip() for e in (case.get("exclude_keywords") or "").split(",") if e.strip()
    ]
    query_text = f"{case.get('title', '')} {case.get('description', '')}".strip()

    results, source = kiprisplus_client.search_patents(
        query_text=query_text,
        keywords=keywords,
        exclude_keywords=excludes,
        scope=case.get("search_scope", "국내+해외"),
        top_n=int(case.get("top_n", 20)),
    )

    cache_enabled = config.get("cache_enabled", "1") == "1"

    for rank, result in enumerate(results, start=1):
        patent_id = db.upsert_patent(result)
        db.link_case_patent(
            review_case_id=case_id,
            patent_id=patent_id,
            rank=rank,
            similarity_score=float(result.get("similarity_score", 0.0)),
        )
        if cache_enabled:
            # Persist any detail fields we already have (text + metadata only).
            db.save_patent_details(
                patent_id=patent_id,
                claims_text=result.get("claims_text", ""),
                bibliographic={
                    "ipc": result.get("ipc", ""),
                    "cpc": result.get("cpc", ""),
                    "legal_status": result.get("legal_status", ""),
                    "registration_no": result.get("registration_no", ""),
                },
                drawing_meta={"drawing_urls": result.get("drawing_urls", [])},
            )

    return len(results), source


def ensure_details(patent_id: int) -> dict:
    """Return cached details for a patent, fetching from KIPRISPlus if needed.

    Output keys: ``claims_text`` (str), ``drawing_urls`` (list), ``bibliographic`` (dict).
    """
    cached = db.get_patent_details(patent_id)
    have_claims = bool(cached and cached.get("claims_text"))
    have_drawings = bool(
        cached and cached.get("drawing_meta", {}).get("drawing_urls")
    )

    if cached and have_claims and have_drawings:
        return _shape_details(cached)

    # Try to enrich from KIPRISPlus when a key is available and data missing.
    patent = db.get_patent(patent_id)
    if patent and config.has_kiprisplus() and patent.get("application_no"):
        app_no = patent["application_no"]
        claims_text = cached.get("claims_text", "") if cached else ""
        drawing_urls = (
            cached.get("drawing_meta", {}).get("drawing_urls", []) if cached else []
        )
        try:
            if not claims_text:
                claims_text = kiprisplus_client.get_patent_claims(app_no)
            if not drawing_urls:
                drawing_urls = kiprisplus_client.get_patent_drawings(app_no)
            db.save_patent_details(
                patent_id=patent_id,
                claims_text=claims_text,
                bibliographic=(cached or {}).get("bibliographic", {}),
                drawing_meta={"drawing_urls": drawing_urls},
            )
            cached = db.get_patent_details(patent_id)
        except Exception:
            # Keep whatever we have; the UI will show what is available.
            pass

    return _shape_details(cached or {})


def _shape_details(cached: dict) -> dict:
    return {
        "claims_text": cached.get("claims_text", "") if cached else "",
        "drawing_urls": (cached.get("drawing_meta", {}) or {}).get("drawing_urls", [])
        if cached
        else [],
        "bibliographic": cached.get("bibliographic", {}) if cached else {},
    }


def cache_usage() -> dict:
    """Return rough cache usage stats for the Settings screen."""
    return {
        "patents": db.count_rows("patents"),
        "detail_rows": db.count_rows("patent_details_cache"),
        "review_cases": db.count_rows("review_cases"),
        "temporary_cases": len(db.list_temporary_cases()),
    }
