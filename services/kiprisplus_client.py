"""KIPRISPlus API client.

KIPRISPlus (http://plus.kipris.or.kr) is the Korean Intellectual Property
Rights Information Service open API. This module isolates every network call
behind a function so the rest of the app never talks to the API directly.

Notes
-----
* The patent/utility search service path on KIPRISPlus is
  ``patUtiliInfoSearchSevice`` (this is KIPRIS's own spelling). The access key
  is passed as ``accessKey`` by default; both the service path and key parameter
  name can be overridden in settings if a given account uses different values.
* Responses are parsed namespace-agnostically and defensively. On any failure
  callers fall back to the clearly-labelled sample dataset
  (see ``services.sample_data``) and the UI shows a sample-mode banner. We never
  fake a successful API response.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

from analyzers import similarity
from services import sample_data
from utils import config

BASE_URL = "http://plus.kipris.or.kr/openapi/rest"
DEFAULT_SERVICE = "patUtiliInfoSearchSevice"
TIMEOUT = 20


class KiprisError(Exception):
    """Raised when a KIPRISPlus call cannot be completed."""


# ---------------------------------------------------------------------------
# Low-level request helper
# ---------------------------------------------------------------------------
def _service() -> str:
    return config.get("kipris_service", DEFAULT_SERVICE) or DEFAULT_SERVICE


def _key_param() -> str:
    return config.get("kipris_key_param", "accessKey") or "accessKey"


def _request(operation: str, params: dict) -> ET.Element:
    """GET a KIPRISPlus operation and return the parsed XML root element."""
    key = config.get_kiprisplus_key()
    if not key:
        raise KiprisError("KIPRISPlus API Key가 설정되지 않았습니다.")
    params = {**params, _key_param(): key}
    url = f"{BASE_URL}/{_service()}/{operation}"
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise KiprisError(f"네트워크 오류: {exc.__class__.__name__}") from exc
    resp.raise_for_status()

    body = resp.content
    text_head = resp.text[:200].lstrip().lower()
    if text_head.startswith("<!doctype html") or text_head.startswith("<html"):
        raise KiprisError(
            "XML이 아닌 HTML 응답을 받았습니다. 서비스 경로/Key를 확인하세요. "
            f"(응답 시작: {resp.text[:120].strip()})"
        )
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise KiprisError(
            f"KIPRISPlus 응답을 해석할 수 없습니다: {exc}. "
            f"(응답 시작: {resp.text[:160].strip()})"
        ) from exc

    _raise_on_api_error(root)
    return root


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _get(node: ET.Element, *names: str) -> str:
    """Return the first descendant text whose local tag name matches."""
    wanted = set(names)
    for el in node.iter():
        if _local(el.tag) in wanted and el.text and el.text.strip():
            return el.text.strip()
    return ""


def _iter_items(root: ET.Element) -> list[ET.Element]:
    return [el for el in root.iter() if _local(el.tag) == "item"]


def _raise_on_api_error(root: ET.Element) -> None:
    """Raise if the response carries an explicit KIPRIS error code."""
    code = ""
    msg = ""
    for el in root.iter():
        name = _local(el.tag)
        if name in ("resultCode", "successYN") and el.text:
            code = el.text.strip()
        elif name in ("resultMsg", "message") and el.text:
            msg = el.text.strip()
    ok_codes = {"00", "000", "0", "success", "ok", "y", "true"}
    if code and code.lower() not in ok_codes and not _iter_items(root):
        raise KiprisError(f"KIPRISPlus 오류 [{code}] {msg or '메시지 없음'}")


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def normalize_patent_result(item: ET.Element, country: str = "KR") -> dict:
    """Map a raw KIPRISPlus result item to the IP3 patent dict shape."""
    return {
        "country": country,
        "application_no": _get(item, "applicationNumber"),
        "publication_no": _get(item, "openNumber", "publicationNumber"),
        "registration_no": _get(item, "registerNumber"),
        "title": _get(item, "inventionName", "inventionTitle", "title"),
        "applicant": _get(item, "applicantName", "applicant"),
        "inventor": _get(item, "inventorName", "inventor"),
        "abstract": _get(item, "astrtCont", "abstract", "abstractInfo"),
        "filing_date": _get(item, "applicationDate"),
        "publication_date": _get(item, "openDate", "publicationDate"),
        "registration_date": _get(item, "registerDate", "registrationDate"),
        "legal_status": _get(item, "registerStatus", "lastValue", "legalStatus"),
        "ipc": _get(item, "ipcNumber", "ipc"),
        "cpc": _get(item, "cpcNumber", "cpc"),
        "representative_drawing_url": _get(item, "drawing", "bigDrawing", "imagePath"),
        "source_url": _get(item, "documentUrl", "url"),
        "drawing_urls": [],
        "claims_text": "",
        "similarity_score": 0.0,
    }


# ---------------------------------------------------------------------------
# Search services
# ---------------------------------------------------------------------------
def search_domestic_patents(query: str, top_n: int = 20) -> list[dict]:
    """Free-text search of Korean patents/utility models (getWordSearch)."""
    root = _request("getWordSearch", {"word": query, "numOfRows": top_n, "pageNo": 1})
    return [normalize_patent_result(it, country="KR") for it in _iter_items(root)]


def search_foreign_patents(query: str, top_n: int = 20) -> list[dict]:
    """Foreign patent search.

    TODO: KIPRISPlus serves foreign collections (US/EP/JP/CN/PCT) through
    dedicated services that differ from the domestic one. Until the exact
    service/parameters for the desired collections are confirmed, this returns
    an empty list rather than guessing (the domestic results still surface).
    """
    return []


def get_patent_bibliography(application_no: str) -> dict:
    """Detailed bibliographic info for one application."""
    root = _request(
        "getBibliographyDetailInfoSearch", {"applicationNumber": application_no}
    )
    items = _iter_items(root)
    return normalize_patent_result(items[0], country="KR") if items else {}


def get_patent_claims(application_no: str) -> str:
    """Claim text for one application.

    TODO: confirm the exact claim operation name and element. We try the
    bibliography-detail response (which often includes claims) and any element
    whose local name contains 'claim'.
    """
    try:
        root = _request(
            "getBibliographyDetailInfoSearch", {"applicationNumber": application_no}
        )
    except KiprisError:
        return ""
    claims = [
        el.text.strip()
        for el in root.iter()
        if "claim" in _local(el.tag).lower() and el.text and el.text.strip()
    ]
    return "\n".join(claims)


def get_patent_drawings(application_no: str) -> list[str]:
    """Drawing image URLs / metadata for one application (URLs only)."""
    try:
        root = _request(
            "getBibliographyDetailInfoSearch", {"applicationNumber": application_no}
        )
    except KiprisError:
        return []
    urls = []
    for el in root.iter():
        if _local(el.tag) in ("drawing", "bigDrawing", "path", "imagePath"):
            if el.text and el.text.strip().startswith("http"):
                urls.append(el.text.strip())
    return urls


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

    Returns ``(results, source)`` where ``source`` is ``"kiprisplus"`` or
    ``"sample"`` so the UI can be honest about the data origin.
    """
    keywords = keywords or []
    excludes = [e.lower() for e in (exclude_keywords or [])]
    query = query_text
    if keywords:
        query = f"{query_text} {' '.join(keywords)}".strip()

    if not config.has_kiprisplus():
        return sample_data.search(query_text, keywords, exclude_keywords, scope, top_n), "sample"

    try:
        results: list[dict] = []
        if scope in ("국내", "국내+해외"):
            results.extend(search_domestic_patents(query, top_n))
        if scope in ("해외", "국내+해외"):
            results.extend(search_foreign_patents(query, top_n))

        # Filter excludes + score similarity (KIPRIS does not return a score).
        basis = query_text + " " + " ".join(keywords)
        scored = []
        for r in results:
            hay = " ".join([r.get("title", ""), r.get("abstract", "")]).lower()
            if any(ex and ex in hay for ex in excludes):
                continue
            r["similarity_score"] = similarity.score(
                basis, r.get("title", "") + " " + r.get("abstract", "")
            )
            scored.append(r)
        scored.sort(key=lambda r: r["similarity_score"], reverse=True)
        return scored[:top_n], "kiprisplus"
    except (requests.RequestException, KiprisError):
        # Never break the workflow: fall back to the clearly-labelled sample data.
        return sample_data.search(query_text, keywords, exclude_keywords, scope, top_n), "sample"


def test_connection() -> tuple[bool, str]:
    """Auto-detect a working KIPRISPlus config and save it.

    Tries the known service-path / key-parameter combinations, and on success
    stores ``kipris_service`` and ``kipris_key_param`` in settings so later calls
    use the right values. Designed to be driven by the Settings screen button —
    no command line needed.
    """
    key = config.get_kiprisplus_key()
    if not key:
        return False, "미연결: API Key가 설정되지 않았습니다."

    combos = [
        ("patUtiliInfoSearchSevice", "accessKey"),
        ("patUtiliInfoSearchSevice", "ServiceKey"),
        ("patUtilityInfoSearchService", "accessKey"),
        ("patUtilityInfoSearchService", "ServiceKey"),
    ]
    last_detail = ""
    for service, key_param in combos:
        url = f"{BASE_URL}/{service}/getWordSearch"
        params = {"word": "전기", "numOfRows": 1, "pageNo": 1, key_param: key}
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last_detail = f"네트워크 오류({exc.__class__.__name__})"
            continue
        try:
            root = ET.fromstring(r.content)
        except ET.ParseError:
            last_detail = f"HTTP {r.status_code} · {r.text[:120].strip()}"
            continue
        # Check for an explicit error code with no items.
        items = _iter_items(root)
        codes = [
            e.text.strip()
            for e in root.iter()
            if _local(e.tag) in ("resultCode", "successYN") and e.text
        ]
        msgs = [
            e.text.strip()
            for e in root.iter()
            if _local(e.tag) in ("resultMsg", "message") and e.text
        ]
        bad = codes and codes[0].lower() not in {"00", "000", "0", "success", "ok", "y", "true"}
        if items or (not bad and root is not None and not msgs):
            config.set("kipris_service", service)
            config.set("kipris_key_param", key_param)
            return True, f"연결됨 · 서비스 {service}, 파라미터 {key_param}"
        last_detail = f"code={codes[0] if codes else '?'} msg={msgs[0] if msgs else '?'}"

    return False, (
        "오류: 동작하는 설정을 찾지 못했습니다. 키/권한을 확인하세요. "
        f"(마지막 응답: {last_detail})"
    )
