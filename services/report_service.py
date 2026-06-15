"""Report generation service for IP3 (PDF + Excel)."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from exporters import excel_exporter, pdf_exporter
from utils import config, db


def _safe_name(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", text).strip("_")
    return text or "review"


def build_report_data(case_id: int) -> tuple[dict | None, list[dict], int | None]:
    """Return (case, comparison results, run_id) for the latest comparison run."""
    case = db.get_review_case(case_id)
    if not case:
        return None, [], None
    run = db.get_latest_comparison_run(case_id)
    if not run:
        return case, [], None
    results = db.get_comparison_results(run["id"])
    return case, results, run["id"]


def generate(case_id: int, report_type: str) -> Path:
    """Generate a report of the given type ('PDF' or 'Excel'); returns the path."""
    case, results, run_id = build_report_data(case_id)
    if not case:
        raise ValueError("검토 케이스를 찾을 수 없습니다.")
    if not results:
        raise ValueError("비교분석 결과가 없습니다. 먼저 선택 특허 비교분석을 실행하세요.")

    report_dir = config.get_report_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"IP3_{_safe_name(case.get('title', ''))}_{stamp}"

    if report_type == "PDF":
        path = pdf_exporter.export(case, results, report_dir / f"{base}.pdf")
    elif report_type == "Excel":
        path = excel_exporter.export(case, results, report_dir / f"{base}.xlsx")
    else:
        raise ValueError(f"지원하지 않는 리포트 형식: {report_type}")

    db.record_report(case_id, run_id, report_type, str(path))
    return path
