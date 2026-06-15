"""IP3 API 진단 스크립트 (로컬 실행용).

이 클라우드 세션에서는 외부 인터넷이 차단되어 API 테스트를 할 수 없습니다.
네트워크가 정상인 본인 PC에서 아래처럼 실행하세요.

    python check_api.py

키는 .env 또는 앱 설정(data/ip3.db)에서 자동으로 읽습니다.
직접 넘길 수도 있습니다:

    python check_api.py --kipris 키값 --gemini 키값

KIPRISPlus는 계정에 따라 키 파라미터명/서비스 경로가 다를 수 있어,
여러 조합을 자동으로 시도하고 어떤 조합이 동작하는지 표시합니다.
출력 결과를 그대로 복사해 알려주시면 설정을 정확히 맞춰드립니다.
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET

import requests

try:
    from utils import config
except Exception:  # 단독 실행 대비
    config = None

KIPRIS_BASE = "http://plus.kipris.or.kr/openapi/rest"
# (서비스경로, 오퍼레이션, 키파라미터명) 조합 후보
KIPRIS_COMBOS = [
    ("patUtiliInfoSearchSevice", "getWordSearch", "accessKey"),
    ("patUtiliInfoSearchSevice", "getWordSearch", "ServiceKey"),
    ("patUtilityInfoSearchService", "getWordSearch", "accessKey"),
    ("patUtilityInfoSearchService", "getWordSearch", "ServiceKey"),
]


def _mask(key: str) -> str:
    if not key:
        return "(없음)"
    return key[:4] + "…" + key[-4:] if len(key) > 8 else "****"


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def check_kipris(key: str) -> None:
    print("\n" + "=" * 60)
    print(f"[KIPRISPlus] 키: {_mask(key)}")
    print("=" * 60)
    if not key:
        print("  키가 없습니다. --kipris 로 넘기거나 설정에 저장하세요.")
        return

    found = False
    for service, op, key_param in KIPRIS_COMBOS:
        url = f"{KIPRIS_BASE}/{service}/{op}"
        params = {"word": "전기", "numOfRows": 3, "pageNo": 1, key_param: key}
        label = f"  {service}/{op}  (param={key_param})"
        try:
            r = requests.get(url, params=params, timeout=20)
        except requests.RequestException as exc:
            print(f"{label}\n      -> 네트워크 오류: {exc.__class__.__name__}")
            continue
        snippet = r.text[:160].replace("\n", " ").strip()
        try:
            root = ET.fromstring(r.content)
            items = [e for e in root.iter() if _local(e.tag) == "item"]
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
            status = f"HTTP {r.status_code} · XML OK · item {len(items)}개"
            if codes:
                status += f" · code={codes[0]}"
            if msgs:
                status += f" · msg={msgs[0]}"
            print(f"{label}\n      -> {status}")
            if items:
                title = next(
                    (e.text for e in items[0].iter()
                     if _local(e.tag) in ("inventionName", "inventionTitle") and e.text),
                    "",
                )
                print(f"         예시 특허명: {title}")
                print(f"      ✅ 동작하는 조합입니다! 설정값: "
                      f"kipris_service={service}, kipris_key_param={key_param}")
                found = True
                break
        except ET.ParseError:
            print(f"{label}\n      -> HTTP {r.status_code} · XML 아님 · 응답: {snippet}")

    if not found:
        print("\n  ⚠️  동작하는 조합을 찾지 못했습니다. 위 응답 내용을 복사해 알려주세요.")


def check_gemini(key: str) -> None:
    print("\n" + "=" * 60)
    print(f"[Gemini] 키: {_mask(key)}")
    print("=" * 60)
    if not key:
        print("  키가 없습니다. --gemini 로 넘기거나 설정에 저장하세요.")
        return
    try:
        import google.generativeai as genai
    except ImportError:
        print("  google-generativeai 미설치. 설치: pip install google-generativeai")
        return

    genai.configure(api_key=key)
    try:
        models = [
            m.name.split("/")[-1]
            for m in genai.list_models()
            if "generateContent" in (getattr(m, "supported_generation_methods", []) or [])
        ]
    except Exception as exc:
        print(f"  모델 목록 조회 실패: {exc}")
        print("  -> 키가 유효하지 않거나 권한이 없을 수 있습니다.")
        return

    print(f"  generateContent 지원 모델 {len(models)}개:")
    for m in models[:20]:
        print(f"    - {m}")

    candidates = ["gemini-2.0-flash", "gemini-flash-latest", "gemini-2.5-flash"]
    target = next((c for c in candidates if c in models), None)
    if not target:
        target = next((m for m in models if "flash" in m), models[0] if models else None)
    if not target:
        print("  사용 가능한 모델이 없습니다.")
        return
    print(f"\n  '{target}' 모델로 생성 테스트…")
    try:
        model = genai.GenerativeModel(target)
        resp = model.generate_content("한 단어로 'OK' 라고만 답하세요.")
        print(f"  ✅ 응답: {getattr(resp, 'text', '')!r}")
        print(f"  -> 설정 → AI 설정의 'AI 모델' 칸에 '{target}' 입력하면 확실합니다 (비워둬도 자동 탐색).")
    except Exception as exc:
        print(f"  생성 실패: {exc}")


def main() -> None:
    ap = argparse.ArgumentParser(description="IP3 API 진단")
    ap.add_argument("--kipris", default="", help="KIPRISPlus API Key")
    ap.add_argument("--gemini", default="", help="Gemini API Key")
    args = ap.parse_args()

    kipris = args.kipris
    gemini = args.gemini
    if config is not None:
        kipris = kipris or config.get_kiprisplus_key()
        if not gemini and config.get_ai_provider() == "Gemini":
            gemini = config.get_ai_key()

    print("IP3 API 진단 시작 (이 출력 전체를 복사해 공유하면 정확히 도와드립니다)")
    check_kipris(kipris)
    check_gemini(gemini)
    print("\n진단 완료.")


if __name__ == "__main__":
    sys.exit(main())
