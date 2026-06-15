"""KIPRISPlus API client.

KIPRISPlus (http://plus.kipris.or.kr) is the Korean Intellectual Property
Rights Information Service open API. This module isolates every network call
behind a function so the rest of the app never talks to the API directly.

IMPORTANT
---------
The exact KIPRISPlus REST service paths, request parameters and XML response
field names differ per service and are not fully pinned down here. Where the
precise contract is uncertain, the function is structured correctly and the
uncertain part is marked with ``TODO``. We never fake a successful response:
if a key is missing or a call fails, callers fall back to the clearly-labelled
sample dataset (see ``services.sample_data``) and the UI shows a sample-mode
banner.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import requests

from services import sample_data
from utils import config

# Base endpoint for KIPRISPlus open API REST services.
BASE_URL = "http://plus.kipris.or.kr/openapi/rest"
TIMEOUT = 15


class KiprisError(Exception):
    """Raised when a KIPRISPlus call cannot be completed."""


# ---------------------------------------------------------------------------
# Low-level request helper
# ---------------------------------------------------------------------------
def _request(path: str, params: dict[str, Any]) -> ET.Element:
    """Perform a GET request against a KIPRISPlus service and return XML root."""
    key = config.get_kiprisplus_key()
    if not key:
        raise KiprisError("KIPRISPlus API Key가 설정되지 않았습니다.")
    params = {**params, "accessKey": key}
    url = f"{BASE_URL}/{path}"
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    try:
        return ET.fromstring(resp.content)
    except ET.ParseError as exc:  # pragma: no cover - network dependent
        raise KiprisError(f"KIPRISPlus 응답을 해석할 수 없습니다: {exc}") from exc


def _text(node: ET.Element | None, tag: str, default: str = "") -> str:
    if node is None:
        return default
    found = node.find(tag)
    return found.text.strip() if found is not None and found.text else default


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def normalize_patent_result(item: ET.Element, country: str = "KR") -> dict:
    """Map a raw KIPRISPlus result item element to the IP3 patent dict shape.

    TODO: confirm the exact child tag names for the specific KIPRISPlus service
    being used. The tags below follow the common patUtilityInfoSearch schema and
    may need adjustment per service.
    """
    return {
        "country": country,
        "application_no": _text(item, "applicationNumber"),
        "publication_no": _text(item, "openNumber") or _text(item, "publicationNumber"),
        "registration_no": _text(item, "registerNumber"),
        "title": _text(item, "inventionTitle") or _text(item, "title"),
        "applicant": _text(item, "applicantName"),
        "inventor": _text(item, "inventorName"),
        "abstract": _text(item, "astrtCont") or _text(item, "abstract"),
        "filing_date": _text(item, "applicationDate"),
        "publication_date": _text(item, "openDate") or _text(item, "publicationDate"),
        "registration_date": _text(item, "registerDate"),
        "legal_status": _text(item, "registerStatus"),
        "ipc": _text(item, "ipcNumber"),
        "cpc": _text(item, "cpcNumber"),
        "representative_drawing_url": _text(item, "drawing") or _text(item, "imagePath"),
        "source_url": _text(item, "documentUrl"),
        "drawing_urls": [],
        "claims_text": "",
        "similarity_score": 0.0,
    }


# ---------------------------------------------------------------------------
# Search services
# ---------------------------------------------------------------------------
def search_domestic_patents(query: str, top_n: int = 20) -> list[dict]:
    """Search Korean patents/utility models.

    TODO: confirm service path (e.g. ``patUtilityInfoSearchService/getWordSearch``)
    and the parameter name carrying the free-text query.
    """
    root = _request(
        "patUtilityInfoSearchService/getWordSearch",
        {"word": query, "numOfRows": top_n, "pageNo": 1},
    )
    items = root.findall(".//item")
    return [normalize_patent_result(it, country="KR") for it in items]


def search_foreign_patents(query: str, top_n: int = 20) -> list[dict]:
    """Search foreign patents.

    TODO: KIPRISPlus exposes foreign data through dedicated services
    (e.g. forFreeSearch / US/EP/JP/CN services). Confirm the correct service
    path and parameters for the foreign collections that should be queried.
    """
    root = _request(
        "ForeignPatentSearchService/getWordSearch",
        {"word": query, "numOfRows": top_n, "pageNo": 1},
    )
    items = root.findall(".//item")
    return [normalize_patent_result(it, country="") for it in items]


def get_patent_bibliography(application_no: str) -> dict:
    """Fetch detailed bibliographic info for one application.

    TODO: confirm the bibliography service path and response schema.
    """
    root = _request(
        "patUtilityInfoSearchService/getBibliographyDetailInfoSearch",
        {"applicationNumber": application_no},
    )
    item = root.find(".//item")
    if item is None:
        return {}
    return normalize_patent_result(item, country="KR")


def get_patent_claims(application_no: str) -> str:
    """Fetch claim text for one application.

    TODO: confirm the claim service path; KIPRISPlus returns claims as repeated
    elements that must be concatenated.
    """
    root = _request(
        "patUtilityInfoSearchService/getClaimInfoSearch",
        {"applicationNumber": application_no},
    )
    claims = [c.text.strip() for c in root.findall(".//claim") if c.text]
    return "\n".join(claims)


def get_patent_drawings(application_no: str) -> list[str]:
    """Fetch drawing image URLs / metadata for one application.

    TODO: confirm the drawing service path. Per product requirements we keep
    only URLs / metadata, never the image binaries themselves.
    """
    root = _request(
        "patUtilityInfoSearchService/getDrawingInfoSearch",
        {"applicationNumber": application_no},
    )
    return [d.text.strip() for d in root.findall(".//path") if d.text]


# ---------------------------------------------------------------------------
# High-level entry point used by the app
# ---------------------------------------------------------------------------
def search_patents(
    query_text: str,
    keywords: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
    scope: str = "국내+해외",
    top_n: int = 20,
) -> tuple[list[dict], str]:
    """Search patents for the given idea.

    Returns ``(results, source)`` where ``source`` is either ``"kiprisplus"``
    or ``"sample"`` so the UI can be honest about where data came from.
    """
    keywords = keywords or []
    query = query_text
    if keywords:
        query = f"{query_text} {' '.join(keywords)}".strip()

    if not config.has_kiprisplus():
        results = sample_data.search(
            query_text, keywords, exclude_keywords, scope, top_n
        )
        return results, "sample"

    try:
        results: list[dict] = []
        if scope in ("국내", "국내+해외"):
            results.extend(search_domestic_patents(query, top_n))
        if scope in ("해외", "국내+해외"):
            results.extend(search_foreign_patents(query, top_n))
        # TODO: apply exclude_keywords filtering + similarity scoring on the
        # real result set once the response schema is confirmed.
        return results[:top_n], "kiprisplus"
    except (requests.RequestException, KiprisError):
        # Never fail the workflow on a network/contract issue: fall back to
        # the clearly-labelled sample data so the user can still work.
        results = sample_data.search(
            query_text, keywords, exclude_keywords, scope, top_n
        )
        return results, "sample"


def test_connection() -> tuple[bool, str]:
    """Lightweight connectivity check for the Settings screen."""
    if not config.has_kiprisplus():
        return False, "미연결: API Key가 설정되지 않았습니다."
    try:
        search_domestic_patents("test", top_n=1)
        return True, "연결됨"
    except requests.RequestException as exc:
        return False, f"오류: 네트워크 연결 실패 ({exc.__class__.__name__})"
    except KiprisError as exc:
        return False, f"오류: {exc}"
