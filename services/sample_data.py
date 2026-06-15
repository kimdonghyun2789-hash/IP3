"""Sample patent dataset for offline / development use.

This module is **not** a stand-in that pretends to be the KIPRISPlus API.
It is an explicitly-labelled local dataset used only when no KIPRISPlus API key
is configured, so the full IP3 workflow can be demonstrated end to end. The UI
shows a clear "샘플 데이터 모드" banner whenever this data is used.

Real searches go through ``services.kiprisplus_client``.
"""
from __future__ import annotations

from utils import text_utils

# A small, hand-written set of realistic-looking sample records. The drawing
# URLs are placeholder image services so thumbnails render during development.
_SAMPLE_PATENTS: list[dict] = [
    {
        "country": "KR",
        "application_no": "1020090112315",
        "publication_no": "KR1020110055086A",
        "registration_no": "",
        "title": "PC 중공기둥의 중공부 배수를 위한 배수 슬리브 매립 구조",
        "applicant": "한국건설기술연구원",
        "inventor": "김중공",
        "abstract": "본 발명은 프리캐스트 콘크리트(PC) 중공기둥의 중공부에 유입된 물을 "
        "외부로 배출하기 위한 배수 슬리브를 생산 단계에서 선매립하는 구조에 관한 것이다. "
        "중공부 하단에 배수 슬리브를 선매립하여 시공 후 별도 천공 없이 배수가 가능하다.",
        "filing_date": "2009-11-26",
        "publication_date": "2011-05-25",
        "registration_date": "",
        "legal_status": "공개",
        "ipc": "E04C 3/34",
        "cpc": "E04C 3/34",
        "claims_text": "청구항 1. PC 중공기둥의 중공부 하단에 선매립되는 배수 슬리브를 포함하는, "
        "중공부 배수 구조.\n청구항 2. 제1항에 있어서, 상기 배수 슬리브는 생산 단계에서 "
        "거푸집에 고정되어 매립되는 것을 특징으로 하는 구조.",
        "drawing_count": 4,
    },
    {
        "country": "CN",
        "application_no": "CN200910231586",
        "publication_no": "CN101736859A",
        "registration_no": "",
        "title": "钢筋混凝土空心柱 (Reinforced concrete hollow column)",
        "applicant": "Shandong University of Science and Technology",
        "inventor": "Fanying Kong",
        "abstract": "A reinforced concrete hollow column. The center of the column is "
        "sleeved with a pipe to form a hollow structure, lowering self weight and saving "
        "concrete. The column can be used as a drainage pipe or threading pipe in a building.",
        "filing_date": "2009-11-26",
        "publication_date": "2010-06-16",
        "registration_date": "",
        "legal_status": "Active",
        "ipc": "E04C 3/34",
        "cpc": "E04C 3/34",
        "claims_text": "Claim 1. A reinforced concrete hollow column comprising a central "
        "pipe forming a hollow structure used as a drainage pipe.",
        "drawing_count": 3,
    },
    {
        "country": "KR",
        "application_no": "1020150088342",
        "publication_no": "KR1020170006789A",
        "registration_no": "KR101998765B1",
        "title": "현장 타설 콘크리트 기둥의 우수 배수 개구부 구조",
        "applicant": "대한건설",
        "inventor": "이배수",
        "abstract": "현장에서 타설되는 콘크리트 기둥에 우수 배수를 위한 개구부를 형성하는 "
        "구조에 관한 것으로, 기둥 측면에 배수구를 두어 내부에 고인 물을 배출한다.",
        "filing_date": "2015-06-22",
        "publication_date": "2017-01-23",
        "registration_date": "2019-06-30",
        "legal_status": "등록",
        "ipc": "E04H 9/14",
        "cpc": "E04H 9/14",
        "claims_text": "청구항 1. 콘크리트 기둥의 측면에 형성된 배수 개구부를 포함하는 배수 구조.",
        "drawing_count": 5,
    },
    {
        "country": "US",
        "application_no": "US14/512,330",
        "publication_no": "US20160102456A1",
        "registration_no": "",
        "title": "Drainage sleeve for precast concrete structural members",
        "applicant": "Precast Solutions Inc.",
        "inventor": "John A. Carter",
        "abstract": "A drainage sleeve embedded in a precast concrete structural member "
        "during fabrication to drain water accumulated in an internal cavity without "
        "field drilling. The sleeve is positioned in the formwork prior to casting.",
        "filing_date": "2014-10-10",
        "publication_date": "2016-04-14",
        "registration_date": "",
        "legal_status": "Pending",
        "ipc": "E04C 5/01",
        "cpc": "E04C 5/01",
        "claims_text": "Claim 1. A precast concrete member having a drainage sleeve embedded "
        "during fabrication within an internal cavity to allow drainage of accumulated water.",
        "drawing_count": 6,
    },
    {
        "country": "KR",
        "application_no": "1020180044551",
        "publication_no": "KR1020190120033A",
        "registration_no": "",
        "title": "프리캐스트 중공 슬래브의 결로수 배출 장치",
        "applicant": "한국토지주택공사",
        "inventor": "박결로",
        "abstract": "프리캐스트 중공 슬래브 내부에 발생하는 결로수를 배출하기 위한 장치로, "
        "중공부와 연결된 배수관을 통해 외부로 수분을 배출한다.",
        "filing_date": "2018-04-18",
        "publication_date": "2019-10-22",
        "registration_date": "",
        "legal_status": "공개",
        "ipc": "E04B 5/48",
        "cpc": "E04B 5/48",
        "claims_text": "청구항 1. 중공 슬래브의 중공부와 연결된 배수관을 포함하는 결로수 배출 장치.",
        "drawing_count": 2,
    },
    {
        "country": "JP",
        "application_no": "JP2012-145678",
        "publication_no": "JP2014-009876A",
        "registration_no": "JP5876543B2",
        "title": "中空コンクリート柱の排水構造 (Drainage structure of hollow concrete column)",
        "applicant": "大成建設株式会社",
        "inventor": "山田太郎",
        "abstract": "中空コンクリート柱の内部に溜まった水を排出するための排水構造に関する。"
        "柱の下部に排水孔を設け、内部の水を外部へ導く。",
        "filing_date": "2012-06-28",
        "publication_date": "2014-01-20",
        "registration_date": "2016-02-05",
        "legal_status": "登録",
        "ipc": "E04C 3/30",
        "cpc": "E04C 3/30",
        "claims_text": "請求項1. 中空コンクリート柱の下部に設けられた排水孔を備える排水構造。",
        "drawing_count": 3,
    },
    {
        "country": "KR",
        "application_no": "1020200099887",
        "publication_no": "KR1020220018822A",
        "registration_no": "",
        "title": "교량 중공 교각의 내부 배수 시스템",
        "applicant": "한국도로공사",
        "inventor": "최교량",
        "abstract": "교량의 중공 교각 내부에 유입되는 우수 및 결로수를 배출하기 위한 "
        "배수 시스템으로, 교각 하부에 집수정과 배수관을 구비한다.",
        "filing_date": "2020-08-11",
        "publication_date": "2022-02-15",
        "registration_date": "",
        "legal_status": "공개",
        "ipc": "E01D 19/08",
        "cpc": "E01D 19/08",
        "claims_text": "청구항 1. 중공 교각 하부의 집수정과 배수관을 포함하는 내부 배수 시스템.",
        "drawing_count": 4,
    },
    {
        "country": "CN",
        "application_no": "CN201810556677",
        "publication_no": "CN108708453A",
        "registration_no": "",
        "title": "预制混凝土柱排水套管 (Drainage casing for precast concrete column)",
        "applicant": "中建科技有限公司",
        "inventor": "Wang Lei",
        "abstract": "A drainage casing pre-embedded in a precast concrete column for "
        "discharging water from the hollow part of the column, installed before casting.",
        "filing_date": "2018-06-01",
        "publication_date": "2018-10-26",
        "registration_date": "",
        "legal_status": "Active",
        "ipc": "E04C 3/34",
        "cpc": "E04C 3/34",
        "claims_text": "Claim 1. A precast concrete column with a drainage casing pre-embedded "
        "for discharging water from the hollow part.",
        "drawing_count": 5,
    },
]


def _drawing_urls(seed: str, count: int) -> list[str]:
    """Placeholder drawing image URLs (development only)."""
    count = max(1, min(count, 8))
    urls = []
    for i in range(count):
        # Deterministic placeholder thumbnails based on the patent number.
        urls.append(f"https://placehold.co/240x200/eef2fb/2563EB?text={seed}-{i + 1}")
    return urls


def _matches_scope(country: str, scope: str) -> bool:
    if scope == "국내":
        return country == "KR"
    if scope == "해외":
        return country != "KR"
    return True


def search(
    query_text: str,
    keywords: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
    scope: str = "국내+해외",
    top_n: int = 20,
) -> list[dict]:
    """Return scored sample patents relevant to the query.

    Results are ranked by simple token overlap with the idea text so different
    searches surface different orderings. This is development data only.
    """
    keywords = keywords or []
    exclude_keywords = [e.lower() for e in (exclude_keywords or [])]
    basis = query_text + " " + " ".join(keywords)

    scored = []
    for idx, p in enumerate(_SAMPLE_PATENTS):
        if not _matches_scope(p["country"], scope):
            continue
        haystack = " ".join([p["title"], p["abstract"], p["claims_text"]]).lower()
        if any(ex and ex in haystack for ex in exclude_keywords):
            continue
        score = text_utils.jaccard(basis, p["title"] + " " + p["abstract"])
        # Keyword bonus
        for kw in keywords:
            if kw.lower() in haystack:
                score += 0.08
        similarity = round(min(0.99, 0.35 + score) * 100, 1)
        seed = (p["publication_no"] or p["application_no"])[-4:] or str(idx)
        record = dict(p)
        record["similarity_score"] = similarity
        record["representative_drawing_url"] = _drawing_urls(seed, 1)[0]
        record["drawing_urls"] = _drawing_urls(seed, p.get("drawing_count", 3))
        record["source_url"] = f"https://patents.google.com/?q={record['publication_no']}"
        scored.append(record)

    scored.sort(key=lambda r: r["similarity_score"], reverse=True)
    return scored[:top_n]
