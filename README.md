# IP³ — 아이디어 기반 특허 검토 플랫폼

IP³는 단순 특허 검색기가 아니라, **아이디어 입력 → 유사특허 검색 → 사용자가 특허 선택 → 선택 특허 비교분석** 흐름을 갖는 실무형 특허 검토 도구입니다.

```
검색은 자동
비교분석은 사용자가 선택 후 수동 실행
```

IP³의 세 가지 IP:
- **Intellectual Property** — 특허·청구항·도면·서지정보
- **Idea-to-Patent** — 내 아이디어를 특허 검토 관점으로 연결
- **Intelligence Platform** — 검색어 확장·내용 정리·유사점/차이점 분석

---

## 1. Python 설치 후 실행하는 방법

1. [Python 3.10+](https://www.python.org/downloads/) 설치 (설치 시 *Add Python to PATH* 체크)
2. 명령 프롬프트에서 프로젝트 폴더로 이동
3. 의존성 설치
   ```bash
   python -m pip install -r requirements.txt
   ```
4. 앱 실행
   ```bash
   python -m streamlit run app.py
   ```
5. 브라우저에서 `http://localhost:8501` 접속 (보통 자동으로 열림)

## 2. run_ip3.bat 실행 방법 (Windows 권장)

- `run_ip3.bat` 파일을 **더블클릭**합니다.
- 최초 실행 시 필요한 패키지를 자동 설치한 뒤 Streamlit 앱이 실행됩니다.
- 브라우저가 자동으로 열립니다.

## 3. IP3.exe 생성 방법

- `build_exe.bat` 파일을 **더블클릭**합니다.
- PyInstaller가 `dist/IP3.exe` 를 생성합니다.

> **한계 안내:** Streamlit 앱은 실행 시 `app.py`, `pages/`, `components/` 등 소스
> 파일을 필요로 합니다. 따라서 `IP3.exe`는 단독 파일만으로는 동작하지 않고, **소스
> 폴더와 같은 위치**에 두고 실행해야 합니다. 환경에 따라 PyInstaller 패키징이
> 실패할 수 있으며, 그 경우 **`run_ip3.bat` 더블클릭 실행을 우선 사용**하세요.

## 4. API Key 설정 방법

API Key 없이도 **샘플 데이터 모드**로 전체 기능을 사용할 수 있습니다.
실제 검색·AI 비교분석을 사용하려면 키를 입력하세요.

방법 1 — 앱 내 설정 화면:
1. 좌측 메뉴 → **설정**
2. **API 설정** 탭에서 KIPRISPlus API Key / AI API Key 입력 → **저장**
3. **연결 테스트**로 상태 확인
4. **AI 설정** 탭에서 AI Provider 선택 (Gemini / OpenAI / Anthropic / Local-Other / 사용 안 함)

방법 2 — `.env` 파일:
- `.env.example` 를 복사해 `.env` 로 만들고 값을 채웁니다.
- 설정 화면에 입력한 값이 `.env` 보다 우선합니다.

선택 AI Provider 패키지(사용하는 것만 설치):
```bash
pip install openai                 # OpenAI
pip install google-generativeai    # Gemini
pip install anthropic              # Anthropic
```

## 5. 데이터 저장 위치

- SQLite DB: `data/ip3.db`
- 저장 항목: 검색 조건/결과, 특허 텍스트·메타정보, 청구항, 비교분석 결과, 관심특허 상태, 검토 메모, 리포트 경로
- **저장하지 않는 것:** 도면 이미지 파일, 원문 PDF, 대용량 첨부 (도면은 URL/메타정보만)

## 6. 리포트 저장 위치

- 기본 폴더: `data/exports/`
- 형식: **PDF**, **Excel** (비교분석 완료 후 비교분석 탭에서 생성)
- 설정 → 데이터 관리 → *리포트 폴더 경로* 에서 위치 확인

## 7. 캐시 정리 방법

- 설정 → **데이터 관리** 탭
- **캐시 정리** — 특허 상세정보 캐시 삭제
- **임시저장 삭제** — 임시저장 검토 케이스 일괄 삭제
- **DB 백업** — DB 파일을 리포트 폴더로 백업 + 다운로드

---

## 화면 / 메뉴 구조

```
+ 새 검토
홈
프로젝트
  검토 케이스
  보관함
설정
```

- **새 검토** — 아이디어명/설명 입력, 상세 옵션, 검토 시작
- **결과 화면** — 3단 레이아웃(사이드바·검토 케이스 패널·결과 영역) + 결과/관심특허/비교분석 탭
- **관심특허/보관함** — 케이스 단위 관심특허 / 전체 라이브러리
- **설정** — API·검색·AI·데이터 관리

## 프로젝트 구조

```
app.py                  # 라우터 (Streamlit 진입점)
app_launcher.py         # exe 패키징용 런처
pages/                  # 화면별 render() 모듈
components/             # 사이드바, 카드, 표, 상세 패널, 진행, 모달, 배지, 레이아웃
services/               # KIPRISPlus 클라이언트, AI 클라이언트, 캐시, 리포트, 샘플 데이터
analyzers/              # 아이디어 구조화, 검색어 확장, 유사도, 비교분석
exporters/              # PDF, Excel
utils/                  # DB, 설정, 텍스트 유틸, 프롬프트 로더
prompts/                # 프롬프트 템플릿(.md)
data/                   # ip3.db, exports/
```

## 동작 원칙

- **검색은 자동, 비교분석은 사용자가 선택 후 수동 실행**합니다. 탭 이동·화면
  재진입·상세 열람만으로는 AI를 재호출하지 않습니다.
- KIPRISPlus API Key가 없으면 **샘플 데이터 모드**로 동작하며 화면에 표시됩니다.
- AI Provider가 없으면 비교분석은 **내장 휴리스틱**(텍스트 근거 기반)으로 동작하며,
  원문에 없는 근거를 임의로 만들지 않고 불명확하면 *확인필요*로 표시합니다.

## 남은 한계

- KIPRISPlus 실 엔드포인트의 정확한 서비스 경로·응답 필드는 `services/kiprisplus_client.py`
  에 `TODO`로 표시되어 있으며, 실제 키로 검증·보정이 필요합니다.
- PyInstaller 단독 실행 파일은 Streamlit 특성상 소스 폴더 동반이 필요합니다.
