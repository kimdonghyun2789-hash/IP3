"""Compare a user's idea to selected patents.

This is the only place that performs the comparison-analysis step. It runs
**only** when the user explicitly triggers it (never on tab switches or
re-renders).

Two modes:
* AI mode  - when a provider is configured, the structured prompt is sent and
  the JSON result is validated.
* Heuristic mode - a deterministic text-overlap analysis used offline. It never
  invents evidence: ``original_evidence`` only contains sentences that actually
  appear in the patent abstract / claims, and uncertain findings are marked
  "확인필요" or "추정".
"""
from __future__ import annotations

import json
import re

from services import ai_client, cache_service
from utils import db, prompts, text_utils

JUDGMENT_VALUES = {"명확", "부분확인", "추정", "확인필요"}

_SENTENCE_SPLIT = re.compile(r"(?<=[.。!?\n])\s+|\n+")


def _idea_text(case: dict) -> str:
    structure = case.get("idea_structure") or {}
    parts = [case.get("title", ""), case.get("description", "")]
    if isinstance(structure, dict):
        parts.extend(str(v) for v in structure.values())
    return " ".join(p for p in parts if p)


def _evidence_sentences(text: str, terms: list[str], limit: int = 3) -> list[str]:
    """Return up to ``limit`` real sentences from ``text`` containing a term."""
    if not text or not terms:
        return []
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    picked: list[str] = []
    lowered_terms = [t.lower() for t in terms]
    for sent in sentences:
        low = sent.lower()
        if any(t in low for t in lowered_terms):
            picked.append(text_utils.truncate(sent, 140))
        if len(picked) >= limit:
            break
    return picked


def heuristic_compare(case: dict, patent: dict) -> dict:
    """Deterministic, evidence-grounded comparison (offline mode)."""
    idea_text = _idea_text(case)
    abstract = patent.get("abstract", "")
    claims = patent.get("claims_text", "")
    patent_text = " ".join([patent.get("title", ""), abstract, claims])

    shared = text_utils.shared_terms(idea_text, patent_text, limit=8)
    overlap = text_utils.jaccard(idea_text, patent_text)

    # Terms emphasised in the idea but absent from the patent text.
    idea_terms = text_utils.keywords_from_text(idea_text, limit=12)
    patent_tokens = set(text_utils.tokenize(patent_text))
    idea_only = [t for t in idea_terms if t not in patent_tokens][:5]

    similar_points: list[str] = []
    if shared:
        similar_points.append(
            "공통 핵심 용어가 확인됨: " + ", ".join(shared)
        )
    if not similar_points:
        similar_points.append("두 문헌에서 직접적으로 일치하는 핵심 용어가 적습니다.")

    different_points: list[str] = []
    if idea_only:
        different_points.append(
            "내 아이디어에서 강조되는 용어가 특허 원문에서 직접 확인되지 않음: "
            + ", ".join(idea_only)
        )
    else:
        different_points.append("원문 기준으로 뚜렷한 차이점이 자동 추출되지 않았습니다.")

    # Where shared terms appear.
    source_locations: list[str] = []
    if any(t in abstract.lower() for t in [s.lower() for s in shared]):
        source_locations.append("요약")
    if any(t in claims.lower() for t in [s.lower() for s in shared]):
        source_locations.append("청구항 1")

    check_points = [
        "위 공통 용어가 내 아이디어의 핵심 구성과 동일한 의미인지 청구항에서 확인 필요",
        "도면에서 구조적 차이가 있는지 추가 확인 필요",
    ]

    evidence = _evidence_sentences(abstract, shared) + _evidence_sentences(claims, shared)
    evidence = evidence[:3]

    # Conservative judgment: heuristic never claims "명확".
    if overlap >= 0.18 and source_locations:
        judgment = "부분확인"
    elif shared:
        judgment = "추정"
    else:
        judgment = "확인필요"

    return {
        "patent_id": patent["id"],
        "similar_points": similar_points,
        "different_points": different_points,
        "check_points": check_points,
        "source_locations": source_locations or ["요약"],
        "original_evidence": evidence,
        "judgment_status": judgment,
        "summary_memo": "자동 텍스트 비교 기준 결과입니다. 원문/도면 확인 후 판단을 보완하세요.",
    }


def _validate_ai_result(data: dict, patent: dict) -> dict:
    """Coerce an AI JSON result into the canonical, validated shape."""

    def as_list(v):
        if isinstance(v, list):
            return [str(x) for x in v if str(x).strip()]
        if v:
            return [str(v)]
        return []

    judgment = str(data.get("judgment_status", "확인필요")).strip()
    if judgment not in JUDGMENT_VALUES:
        judgment = "확인필요"

    return {
        "patent_id": patent["id"],
        "similar_points": as_list(data.get("similar_points")),
        "different_points": as_list(data.get("different_points")),
        "check_points": as_list(data.get("check_points")),
        "source_locations": as_list(data.get("source_locations")),
        "original_evidence": as_list(data.get("original_evidence")),
        "judgment_status": judgment,
        "summary_memo": str(data.get("summary_memo", "")).strip(),
    }


def compare_one(case: dict, patent: dict) -> dict:
    """Compare the idea to a single patent (with claims already attached)."""
    if ai_client.is_available():
        try:
            structure = case.get("idea_structure") or {}
            structure_text = (
                json.dumps(structure, ensure_ascii=False, indent=2)
                if isinstance(structure, dict)
                else str(structure)
            )
            prompt = prompts.render(
                "comparison_analysis",
                idea_title=case.get("title", ""),
                idea_description=case.get("description", ""),
                idea_structure=structure_text,
                patent_title=patent.get("title", ""),
                patent_applicant=patent.get("applicant", ""),
                patent_country=patent.get("country", ""),
                patent_abstract=patent.get("abstract", ""),
                patent_claims=patent.get("claims_text", "") or "(청구항 정보 없음)",
                patent_id=str(patent["id"]),
            )
            data = ai_client.generate_json(prompt)
            return _validate_ai_result(data, patent)
        except ai_client.AIError:
            # Fall back to the heuristic if the AI call fails.
            return heuristic_compare(case, patent)
        except Exception:
            return heuristic_compare(case, patent)
    return heuristic_compare(case, patent)


def run_comparison(case: dict, selected_patent_ids: list[int]) -> int:
    """Run comparison for the selected patents and persist results.

    Returns the comparison_run id.
    """
    run_id = db.create_comparison_run(case["id"], selected_patent_ids)
    for patent_id in selected_patent_ids:
        patent = db.get_patent(patent_id)
        if not patent:
            continue
        details = cache_service.ensure_details(patent_id)
        patent["claims_text"] = details.get("claims_text", "")
        result = compare_one(case, patent)
        db.save_comparison_result(run_id, case["id"], result)
    return run_id
