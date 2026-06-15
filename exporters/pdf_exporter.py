"""PDF report exporter for IP3 using reportlab.

Korean text is rendered with reportlab's bundled CID font (HYSMyeongJo-Medium),
so no external font files are required.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_FONT = "HYSMyeongJo-Medium"
_FONT_REGISTERED = False


def _ensure_font() -> None:
    global _FONT_REGISTERED
    if not _FONT_REGISTERED:
        pdfmetrics.registerFont(UnicodeCIDFont(_FONT))
        _FONT_REGISTERED = True


def _styles():
    _ensure_font()
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "IP3Title", parent=base["Title"], fontName=_FONT, fontSize=18, spaceAfter=8
    )
    h2 = ParagraphStyle(
        "IP3H2", parent=base["Heading2"], fontName=_FONT, fontSize=13,
        spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#1d4ed8"),
    )
    body = ParagraphStyle(
        "IP3Body", parent=base["BodyText"], fontName=_FONT, fontSize=10, leading=15
    )
    small = ParagraphStyle(
        "IP3Small", parent=base["BodyText"], fontName=_FONT, fontSize=9, leading=13,
        textColor=colors.HexColor("#52606d"),
    )
    return title, h2, body, small


def _bullets(items: list[str], style) -> list:
    if not items:
        return [Paragraph("- 없음", style)]
    return [Paragraph(f"• {it}", style) for it in items]


def export(case: dict, results: list[dict], out_path: Path) -> Path:
    """Render a comparison report PDF and return the path."""
    title_s, h2_s, body_s, small_s = _styles()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"IP3 비교분석 리포트 - {case.get('title', '')}",
    )
    flow: list = []

    flow.append(Paragraph("IP³ 비교분석 리포트", title_s))
    flow.append(Paragraph(case.get("title", "(제목 없음)"), h2_s))
    flow.append(Paragraph(case.get("description", ""), body_s))
    flow.append(Spacer(1, 6))

    # Search conditions
    flow.append(Paragraph("검색 조건", h2_s))
    cond = [
        ["검색 범위", case.get("search_scope", "")],
        ["결과 수", str(case.get("top_n", ""))],
        ["핵심 키워드", case.get("keywords", "") or "-"],
        ["제외어", case.get("exclude_keywords", "") or "-"],
    ]
    cond_tbl = Table(cond, colWidths=[35 * mm, 130 * mm])
    cond_tbl.setStyle(_table_style(header=False))
    flow.append(cond_tbl)
    flow.append(Spacer(1, 6))

    # Summary table
    flow.append(Paragraph("비교분석 요약", h2_s))
    head = ["특허명", "주요 유사점", "주요 차이점", "판단 상태"]
    rows = [head]
    for r in results:
        rows.append([
            Paragraph(r.get("title", ""), small_s),
            Paragraph("; ".join(r.get("similar_points", [])[:1]) or "-", small_s),
            Paragraph("; ".join(r.get("different_points", [])[:1]) or "-", small_s),
            Paragraph(r.get("judgment_status", ""), small_s),
        ])
    summary_tbl = Table(rows, colWidths=[55 * mm, 45 * mm, 45 * mm, 20 * mm], repeatRows=1)
    summary_tbl.setStyle(_table_style(header=True))
    flow.append(summary_tbl)

    # Per-patent detail
    flow.append(Paragraph("특허별 상세 비교", h2_s))
    for idx, r in enumerate(results, start=1):
        flow.append(Paragraph(
            f"{idx}. {r.get('title', '')} "
            f"[{r.get('country', '')} {r.get('publication_no', '') or r.get('application_no', '')}]",
            ParagraphStyle("ph", fontName=_FONT, fontSize=11, spaceBefore=10,
                           spaceAfter=4, textColor=colors.HexColor("#102a43")),
        ))
        flow.append(Paragraph(f"판단 상태: {r.get('judgment_status', '')}", small_s))
        flow.append(Paragraph("유사한 점", small_s))
        flow.extend(_bullets(r.get("similar_points", []), body_s))
        flow.append(Paragraph("차이점", small_s))
        flow.extend(_bullets(r.get("different_points", []), body_s))
        flow.append(Paragraph("확인할 점", small_s))
        flow.extend(_bullets(r.get("check_points", []), body_s))
        flow.append(Paragraph("확인 위치", small_s))
        flow.append(Paragraph(", ".join(r.get("source_locations", [])) or "-", body_s))
        flow.append(Paragraph("원문 근거", small_s))
        flow.extend(_bullets(r.get("original_evidence", []), body_s))
        if r.get("summary_memo"):
            flow.append(Paragraph("검토 메모", small_s))
            flow.append(Paragraph(r.get("summary_memo", ""), body_s))

    doc.build(flow)
    return out_path


def _table_style(header: bool) -> TableStyle:
    cmds = [
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd2d9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3ecfb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ]
    else:
        cmds += [("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f6fb"))]
    return TableStyle(cmds)
