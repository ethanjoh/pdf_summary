# CHANGELOG

## [2026-09-01] - 작업 완료 보고서 실패 원인 상세 목록 출력 및 터미널 UI 디자인 전면 개선

### 변경 목적
- 도서 요약 처리 실패 시 실패한 도서명과 구체적인 원인(할당량 소진, 서버 과부하, 파싱 오류 등)을 최종 작업 완료 보고서에서 한눈에 파악할 수 있도록 개선하고, 터미널 CLI 화면의 가독성과 시각적 완성도를 높임.

### 주요 결정 사항
1. **실패 도서 및 상세 원인 수집/출력 (`main.py`)**:
   - `failed_books` 리스트를 통해 실패한 도서명 및 오류 사유를 수집.
   - `QuotaExhaustedError` 시 "Gemini API 일일 무료 할당량(PerDay) 소진 또는 모든 모델 실패" 사유 명시.
   - 일반 `Exception` 시 첫 줄 오류 메시지를 간결하게 추출하여 기록.
   - 최종 완료 보고서 하단에 `[❌ 실패 도서 및 원인 목록]` 박스 섹션 추가.
2. **터미널 UI 디자인 전면 개선 (`main.py`)**:
   - **시작 설정 배너**: 유니코드 박스 프레임(`┌─┐`, `│`, `└─┘`)과 아이콘(📁, 💾, 🤖, ⏱️, 🔄, 📝)을 적용한 정돈된 설정 안내.
   - **파일 탐색 및 현황 분석**: 🟢 완료(스킵) 및 ⏳ 신규 처리 예정 도서 현황 시각화.
   - **도서별 작업 로그**: 구분선(`━━━━━━━━━━━━━━━━━━━━`) 및 단계별 아이콘(📸 북커버, 🧠 AI 분석, ✨ 완료, ⏭️ 스킵, ❌ 에러) 적용.
   - **최종 대시보드**: 더블 라인 박스(`╔═╗`, `║`, `╚═╝`) 및 신규 처리 성공률(`%`) 표시.
3. **단위 테스트 추가 (`test_pdf_processor.py`)**:
   - `test_quota_exhausted_handling`에서 실패 목록(`failed_books`) 수집 및 원인 검증 로직 추가.

### 수정한 파일
- `main.py`: 터미널 UI 디자인 전면 개선, `failed_books` 수집 및 최종 실패 원인 목록 출력 구현
- `test_pdf_processor.py`: 실패 원인 수집 단위 테스트 검증 추가
- `CHANGELOG.md`: 변경 기록 추가

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (실패 원인 수집, QuotaExhaustedError 검증, CLI 인자, 마크다운 추출, 북커버 추출 등 모두 PASS)
- `python main.py --help` CLI 도움말 정상 작동 확인

---

## [2026-09-01] - Gemini API 일일 무료 할당량 소진 시 메인 작업 즉시 안전 종료 처리

### 변경 목적
- 모든 모델(`gemini-3.7-flash`, `gemini-3.6-flash`)의 일일 무료 할당량(PerDay/FreeTier)이 소진되거나 호출이 모두 실패했을 때, 남은 도서들에 대해 매번 35초씩 대기하며 실패 에러를 반복 출력하던 문제를 해결하고 즉시 작업을 안전하게 종료하도록 개선.

### 주요 결정 사항
1. **커스텀 예외 `QuotaExhaustedError` 정의 및 발생 (`summarizer.py`)**:
   - `QuotaExhaustedError` 예외 클래스 정의.
   - `_generate_content_with_retry`에서 모든 모델 시도 실패 시 기존 `RuntimeError` 대신 `QuotaExhaustedError`를 명시적으로 발생.
2. **메인 일괄 처리 루프 즉시 중단 및 쿨다운 스킵 (`main.py`)**:
   - `QuotaExhaustedError` 발생 시 에러 사유 및 즉시 종료 안내를 출력하고 루프를 즉시 탈출(`break`).
   - `finally` 블록의 불필요한 도서 간 쿨다운 대기(`time.sleep`)를 건너뛰어 즉시 최종 `[작업 완료 보고]` 통계를 출력하고 프로그램 종료.
3. **단위 테스트 추가 (`test_pdf_processor.py`)**:
   - `test_quota_exhausted_handling` 단위 테스트 추가: `QuotaExhaustedError` 정의 및 쿨다운 없는 즉시 루프 탈출(break) 시뮬레이션 검증.
4. **가이드 문서 동기화 (`README.md`)**:
   - 일일 무료 한도 소진 시 즉시 안전 종료 동작 안내 반영 및 목록 번호 정렬.

### 수정한 파일
- `summarizer.py`: `QuotaExhaustedError` 클래스 정의 및 모든 모델 소진 시 예외 발생
- `main.py`: `QuotaExhaustedError` catch 및 쿨다운 없는 즉시 탈출(break) 처리
- `test_pdf_processor.py`: 할당량 소진 시 즉시 종료 로직 단위 테스트 추가
- `README.md`: 할당량 보호 및 즉시 종료 안내 반영
- `CHANGELOG.md`: 변경 기록 추가

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (QuotaExhaustedError 검증, CLI 인자, 원문 조건부 저장, 물결표 이스케이프, 태그 정규화, 볼드 공백 보정, Mermaid 문법 보정, 프롬프트 포맷팅, PDF 분할, 시리즈 파싱, 북커버 추출 모두 PASS)

---

## [2026-09-01] - README.md 기술 스택 최신화 (pymupdf4llm, Mermaid, unittest 추가)

### 변경 목적
- 프로젝트에 새롭게 도입된 로컬 마크다운 추출 라이브러리(`pymupdf4llm`) 및 시각화/테스트 도구(`Mermaid.js`, `unittest`)를 `README.md` 기술 스택 목록에 정확히 반영하여 문서 최신성 및 일관성 유지.

### 주요 결정 사항
1. **기술 스택 섹션 갱신 (`README.md`)**:
   - `pymupdf4llm` 추가: PDF 구조 분석 및 로컬 고품질 마크다운 텍스트 추출 역할 명시
   - `PyMuPDF` 역할 상세화 (북커버 렌더링, 메타데이터 추출, 대용량 PDF 분할)
   - `Mermaid.js` (인물 관계도 및 핵심 개념 체계도 다이어그램) 및 `unittest` (내장 단위 테스트 스위트) 항목 추가

### 수정한 파일
- `README.md`: `## 🛠️ 기술 스택` 항목 갱신
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과
- `README.md` 내용 및 기술 스택 일치 확인

---

## [2026-09-01] - `--source` CLI 옵션을 통한 도서 원문 마크다운(_source.md) 조건부 저장 기능 추가

### 변경 목적
- 도서 PDF에서 추출한 원문 마크다운 파일(`{도서명}_source.md`)의 디스크 저장을 기본 비활성화(`False`)하고, 사용자가 `--source` (또는 `-s`) 옵션을 부여한 경우에만 선택적으로 저장할 수 있도록 개선하여 불필요한 디스크 용량 점유를 방지하고 기본 산출물을 깔끔하게 유지.

### 주요 결정 사항
1. **CLI `--source` / `-s` 옵션 추가 (`main.py`)**:
   - `argparse`에 `--source`, `-s` 플래그(`action="store_true"`, 기본값 `False`) 추가.
   - 메인 실행 안내 화면에 소스 마크다운 저장 옵션 활성화 여부 출력.
   - `summarizer.summarize_series_to_markdown` 호출 시 `save_source=args.source` 전달.
2. **원문 마크다운 조건부 저장 로직 구현 (`summarizer.py`)**:
   - `summarize_series_to_markdown` 및 `summarize_pdf_to_markdown` 메서드에 `save_source: bool = False` 파라미터 추가.
   - 텍스트 레이어 추출 후 `save_source`가 `True`일 때만 디스크에 `{도서명}_source.md` 파일 저장 수행.
3. **단위 테스트 및 가이드 문서 갱신 (`test_pdf_processor.py`, `README.md`)**:
   - `test_cli_args` 단위 테스트 추가: 기본 실행 시 `args.source == False`, `--source`/`-s` 옵션 시 `args.source == True` 검증.
   - `save_source` 플래그에 따른 `_source.md` 파일 생성/미생성 검증 테스트 추가.
   - `README.md` CLI 옵션 표 및 산출물 구조 가이드에 `--source` 옵션 설명 갱신.

### 수정한 파일
- `summarizer.py`: `save_source` 파라미터 추가 및 조건부 원문 마크다운 저장 적용
- `main.py`: `--source` / `-s` CLI 인자 추가 및 요약 모듈 연동
- `test_pdf_processor.py`: CLI 인자 및 `save_source` 조건부 저장 단위 테스트 추가
- `README.md`: `--source` 옵션 가이드 및 산출물 설명 갱신
- `CHANGELOG.md`: 변경 기록 추가

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (CLI 인자 파싱, 원문 마크다운 조건부 저장, 마크다운 추출, 볼드 공백 보정, 물결표 이스케이프, 태그 정규화, Mermaid 문법 보정, 프롬프트 포맷팅, PDF 분할, 시리즈 파싱, 북커버 추출 모두 PASS)
- `python main.py --help` CLI 도움말 정상 동작 확인

---

## [2026-09-01] - OCR 완료 PDF 로컬 마크다운 추출 및 Gemini 고속 전송 & 도서 원문(_source.md) 저장 기능 추가

### 변경 목적
- 도서 PDF 파일을 Gemini Files API로 직접 업로드하던 방식을 개선하여, OCR(텍스트 레이어)이 포함된 PDF에서 `pymupdf4llm`/`PyMuPDF`를 통해 로컬에서 구조화된 마크다운 텍스트를 먼저 추출한 뒤 Gemini 프롬프트로 직접 전송함으로써 대기 시간 및 토큰 소모를 대폭 절감.
- 추출된 도서 원문 마크다운 전체 텍스트를 `{도서명}_source.md` 파일로 디스크에 함께 저장하여 3종 산출물 체계 완성.

### 주요 결정 사항
1. **로컬 마크다운 추출 및 원문 파일 저장 구현 (`pdf_processor.py`, `summarizer.py`)**:
   - `extract_markdown_from_pdf` 함수 추가: `pymupdf4llm.to_markdown`을 우선 활용하여 제목, 본문, 표, 서식이 보존된 마크다운을 로컬에서 즉시 추출.
   - `summarize_series_to_markdown`에서 추출된 원문 텍스트를 `{도서명}_source.md` 파일로 디스크에 저장 (단권 및 시리즈 통합).
2. **Gemini 요약 처리 고속화 및 스마트 폴백 (`summarizer.py`)**:
   - 추출된 도서 마크다운 텍스트가 존재하는 경우(텍스트 레이어 있음) 구글 서버 파일 업로드 없이 순수 텍스트 프롬프트로 전송하여 고속 처리.
   - 텍스트 레이어가 없는 순수 스캔본 PDF인 경우 기존 Gemini Files API 멀티모달 비전 방식으로 자동 폴백.
   - 텍스트 모드 토큰 한도 초과 시 텍스트 구간 분할 요약(`_summarize_chunked_text`) 지원.
3. **산출물 3종 세트 파일 체계 구성 (`main.py`, `README.md`)**:
   - `{도서명}_cover.jpg` : 1페이지 고화질 북커버 이미지
   - `{도서명}_review.md` : Gemini 생성 블로그 서평 마크다운
   - `{도서명}_source.md` : PDF에서 추출한 도서 원문 마크다운 전체 텍스트
4. **pymupdf4llm 내부 numpy RuntimeWarning(divide by zero in log) 음소거 처리 (`pdf_processor.py`, `main.py`)**:
   - `pymupdf_layout`의 높이/여백 로그 연산 시 발생하는 불필요한 콘솔 경고 메시지를 `warnings.catch_warnings()` 및 `filterwarnings`로 안전하게 차단.
5. **의존성 및 테스트 (`requirements.txt`, `test_pdf_processor.py`)**:
   - `pymupdf4llm>=0.0.17` 의존성 추가.
   - 마크다운 추출 및 `_source.md` 파일 저장 단위 테스트 추가.

### 수정한 파일
- `pdf_processor.py`: `extract_markdown_from_pdf` 함수 구현
- `summarizer.py`: 마크다운 텍스트 기반 요약, `_source.md` 원문 파일 저장, 청킹 로직 구현, 멀티모달 폴백 유지
- `main.py`: `source_md_path` 경로 전달 및 작업 진행 메시지 갱신
- `requirements.txt`: `pymupdf4llm` 패키지 추가
- `test_pdf_processor.py`: 마크다운 추출 및 원문 저장 단위 테스트 추가
- `README.md`: 로컬 마크다운 추출 및 산출물 3종 구조 안내 갱신
- `CHANGELOG.md`: 변경 기록 추가

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (마크다운 추출, 원문 저장, 볼드 공백 보정, 물결표 이스케이프, 태그 정규화, Mermaid 문법 보정, 프롬프트 포맷팅, PDF 분할, 시리즈 파싱, 북커버 추출 모두 PASS)

---

## [2026-08-31] - 마크다운 물결표(~) 취소선 오인 방지 이스케이프(\~) 처리 및 자동 보정

### 변경 목적
- 마크다운 렌더러(티스토리, 네이버 블로그, 벨로그, 깃허브 등)에서 수치 범위나 문맥에 사용된 `~`(물결표) 기호가 취소선(strikethrough) 또는 아래첨자(subscript) 문법으로 오인되어 서식이 깨지는 문제를 방지하기 위해 `\~`으로 자동 이스케이프 처리.

### 주요 결정 사항
1. **AI 프롬프트 물결표 이스케이프 지침 추가 (`summarizer.py`)**:
   - `SUMMARY_PROMPT_TEMPLATE` 및 `PARTIAL_SUMMARY_PROMPT`의 필수 문법 규칙에 물결표(`~`) 사용 시 백슬래시 이스케이프(`\~`)를 적용하도록 명시 (예: `30\~50자`, `1\~2문장`, `4\~6명`, `1990\~2000년대`).
   - 템플릿 내부 안내 및 예시 문구(`30~50자` -> `30\~50자` 등)를 `\~` 형태로 일괄 정규화.
2. **후처리 함수 `escape_tilde` 구현 및 `postprocess_markdown` 연동 (`summarizer.py`)**:
   - 코드 블록(````...````) 및 인라인 코드(`` `...` ``) 영역을 안전하게 보호하면서 일반 텍스트 영역의 미이스케이프 `~`(`(?<!\\)~`)를 `\~`로 자동 치환.
   - 이미 `\~`로 이스케이프된 경우 중복 이스케이프(`\\~`) 방지.
   - `postprocess_markdown()` 종합 후처리 파이프라인에 `escape_tilde` 연동.
3. **단위 테스트 추가 및 문서화 (`test_pdf_processor.py`, `README.md`)**:
   - `test_escape_tilde` 단위 테스트 추가 (수치 범위, 일반 물결표, 인라인 코드/코드 블록 보호, 중복 이스케이프 방지 등 검증).
   - `README.md` 가이드 문서 내 마크다운 예시 텍스트 갱신 및 렌더링 자동 보정 기능 안내 추가.

### 수정한 파일
- `summarizer.py`: `escape_tilde` 함수 추가, `postprocess_markdown` 연동, 프롬프트 템플릿 규칙 갱신
- `test_pdf_processor.py`: `test_escape_tilde` 단위 테스트 추가 및 종합 후처리 테스트 갱신
- `README.md`: 마크다운 예시 및 후처리 기능 설명 갱신
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (물결표 이스케이프, 태그 정규화, 볼드 공백 보정, Mermaid 문법/가독성 보정, 프롬프트 포맷팅, PDF 분할, 시리즈 파싱, 북커버 추출 모두 PASS)

---

## [2026-08-29] - 폴백 대상 모델에서 gemini-3.5-flash 제외

### 변경 목적
- 도서 요약 품질 유지 및 모델 전환 제한을 위해 일일 할당량 소진 또는 오류 발생 시 대체 모델 목록에서 `gemini-3.5-flash`로 자동 전환되지 않도록 제외.

### 주요 결정 사항
1. **대체 모델 목록 조정 (`summarizer.py`)**:
   - `FALLBACK_MODELS = ["gemini-3.6-flash"]`로 수정하여 `gemini-3.7-flash` 할당량 소진 시 `gemini-3.6-flash`까지만 폴백 시도하도록 설정.
2. **문서 동기화 (`README.md`)**:
   - 폴백 모델 안내 및 기술 스택 설명에서 `gemini-3.5-flash` 항목 제거.

### 수정한 파일
- `summarizer.py`: `FALLBACK_MODELS`에서 `gemini-3.5-flash` 제거
- `README.md`: 모델 폴백 안내 및 기술 스택 갱신
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과

---

## [2026-08-29] - 블로그 플랫폼 태그창 호환을 위한 메타데이터 태그 '#' 제거 및 쉼표 구분 순수 키워드 자동 정규화

### 변경 목적
- 블로그 플랫폼(티스토리, 네이버 블로그, 워드프레스 등)의 태그 입력창에 바로 복사/붙여넣기하여 개별 태그로 자동 등록될 수 있도록, 태그에서 '#' 기호를 제거하고 쉼표(`, `)로 구분된 순수 키워드 목록 형식으로 개선.

### 주요 결정 사항
1. **AI 프롬프트 태그 작성 지침 변경 (`summarizer.py`)**:
   - `SUMMARY_PROMPT_TEMPLATE`의 태그 지침을 '#' 없이 쉼표로 키워드를 나열(`[장르], [핵심키워드1], [핵심키워드2], [추천독자층]`)하도록 명시.
2. **후처리 함수 `normalize_tags` 구현 및 `postprocess_markdown` 연동 (`summarizer.py`)**:
   - 정규식을 통해 메타데이터의 태그 라인에서 `#` 기호를 제거하고 쉼표(`, `)로 분리된 순수 키워드 문자열(`키워드1, 키워드2, 키워드3`)로 자동 정규화.
3. **기존 생성 마크다운 파일 223개 일괄 보정 (`output/`)**:
   - `output/` 폴더 내 기존 마크다운 파일들의 추천 태그 라인에서 `#` 기호를 제거하고 쉼표 구분 형식으로 일괄 자동 보정 완료.
4. **단위 테스트 추가 및 문서화 (`test_pdf_processor.py`, `README.md`)**:
   - `test_tag_normalization` 단위 테스트 추가 및 전체 테스트 스위트 검증 완료.

### 수정한 파일
- `summarizer.py`: `normalize_tags` 함수 추가, `postprocess_markdown` 연동, `SUMMARY_PROMPT_TEMPLATE` 태그 규칙 갱신
- `test_pdf_processor.py`: 태그 '#' 제거 및 쉼표 구분 단위 테스트 추가 및 테스트 실행기 연동
- `README.md`: 마크다운 산출물 예시 태그 포맷 갱신
- `output/` 하위 마크다운 파일들: 태그 '#' 제거 및 쉼표 구분 일괄 적용
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (태그 정규화, 볼드 공백 정규화, Mermaid 문법/가독성 보정, 프롬프트 포맷팅, PDF 분할, 시리즈 파싱, 북커버 추출 모두 PASS)

---

## [2026-08-28] - Gemini API 503 UNAVAILABLE(서버 일시 과부하) 자동 재시도 및 모델 폴백 대응

### 변경 목적
- Google Gemini API 서버의 일시적 트래픽 급증으로 `503 UNAVAILABLE` (This model is currently experiencing high demand) 에러 발생 시, 작업이 중단되지 않고 자동 대기 후 재시도 및 대체 모델로 폴백하여 작업을 끝까지 완수하도록 개선.

### 주요 결정 사항
1. **503 / 서버 일시 과부하 감지 및 지수 백오프 대기 재시도 (`summarizer.py`)**:
   - `503`, `500`, `UNAVAILABLE`, `high demand` 등 일시적 서버 장애 키워드를 감지하여 15초, 30초, 45초 등 점진적 대기 후 최대 5회까지 자동 재시도하도록 로직 추가.
2. **서버 과부하 지속 시 대체 모델 자동 폴백 (`summarizer.py`)**:
   - 동일 모델에서 서버 과부하가 지속되어 최대 재시도 횟수를 초과할 경우, 즉시 다음 대체 모델(`gemini-3.6-flash`, `gemini-3.5-flash`)로 자동 전환하여 요약 생성 계속 진행.

### 수정한 파일
- `summarizer.py`: `_generate_content_with_retry` 메서드에 503/서버 과부하 자동 재시도 및 대체 모델 폴백 로직 구현
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과

---

## [2026-08-28] - 대용량 PDF 분할 시 Windows 파일 잠금 해제 버그 수정 (Permission denied 해결)

### 변경 목적
- 대용량 PDF 요약 시 토큰 초과로 인해 `split_pdf_into_parts()` 실행 중 `NamedTemporaryFile`이 파일 핸들을 점유한 상태에서 PyMuPDF `part_doc.save()`가 호출되어 Windows 환경에서 `code=2: cannot remove file ...: Permission denied` 오류가 발생하며 작업이 중단되던 현상 해결.

### 주요 결정 사항
1. **임시 파일 핸들 선행 닫기 (`pdf_processor.py`)**:
   - `tempfile.NamedTemporaryFile(..., delete=False)` 생성 직후 `tmp.close()`를 호출하여 Python 프로세스의 파일 핸들을 해제한 뒤 `part_doc.save(tmp.name)`를 실행하도록 순서 보정.
2. **임시 분할 파일 정리 로직 안전성 강화 (`summarizer.py`)**:
   - `_summarize_chunked` 내 `finally` 정리 블록에서 원본 PDF 경로 리스트(`original_paths`)를 명확히 제외하고 실제 임시 파일만 안전하게 `os.unlink()`하도록 정리.
3. **단위 테스트 추가 (`test_pdf_processor.py`)**:
   - 다중 페이지 PDF를 3등분 분할 저장하고 임시 파일 삭제 및 파일 잠금 해제 동작을 검증하는 `test_pdf_split` 테스트 케이스 추가.

### 수정한 파일
- `pdf_processor.py`: `split_pdf_into_parts` 내 `tmp.close()` 호출 시점 조정
- `summarizer.py`: `_summarize_chunked` 임시 파일 정리 조건식 보정
- `test_pdf_processor.py`: PDF 분할 및 임시 파일 관리 단위 테스트 추가
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (PDF 분할 저장/삭제, 프롬프트 포맷팅, 볼드 공백 정규화, Mermaid 문법 보정, 시리즈 파싱, 북커버 추출 모두 PASS)

---

## [2026-08-27] - 프롬프트 템플릿 내 Mermaid init 중괄호 이스케이프 버그 수정 ('init' KeyError 해결)

### 변경 목적
- 도서 요약 처리 시 `SUMMARY_PROMPT_TEMPLATE` 내 Mermaid 테마 지시문(`%%{init: ...}%%`)의 중괄호(`{}`)가 이스케이프되지 않아 `str.format()` 실행 중 `KeyError: 'init'` 에러가 발생하며 도서 요약 생성이 실패하던 버그 수정.

### 주요 결정 사항
1. **프롬프트 템플릿 중괄호 이스케이프 (`summarizer.py`)**:
   - `SUMMARY_PROMPT_TEMPLATE` 내 지시문 지침 및 예시 다이어그램의 `%%{init: {'theme': 'base', ...}}%%`를 `%%{{init: {{'theme': 'base', ...}}}}%%`로 이스케이프 처리하여 문자열 포맷팅 시 `KeyError` 발생 원천 차단.
2. **프롬프트 포맷팅 단위 테스트 추가 (`test_pdf_processor.py`)**:
   - 단일 도서(`SUMMARY_PROMPT_TEMPLATE`), 시리즈 도서 및 분할 통합(`MERGE_SUMMARY_PROMPT`) 포맷팅 유효성을 검증하는 `test_prompt_template_formatting` 테스트 케이스 추가.

### 수정한 파일
- `summarizer.py`: `SUMMARY_PROMPT_TEMPLATE` 내 Mermaid init 중괄호 이스케이프 적용
- `test_pdf_processor.py`: 프롬프트 템플릿 포맷팅 단위 테스트 추가
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (프롬프트 포맷팅, 볼드 공백 정규화, Mermaid 문법 보정, 시리즈 파싱, 북커버 추출 모두 PASS)

---

## [2026-08-26] - 마크다운 볼드(**) 시작/끝 공백 오류 원천 방지 및 후처리 보정 고도화

### 변경 목적
- 마크다운 본문 작성 시 볼드 시작 기호(`**`) 바로 뒤에 공백이 들어가거나(`** 텍스트**`), 한 줄에 여러 볼드 구문이 존재할 때 앞선 닫는 태그와 다음 여는 태그 사이를 볼드로 오인하여 `**` 뒤에 공백이 잘못 삽입되는 현상 해결.
- 볼드 내부 공백으로 인해 마크다운 렌더러에서 굵은 글씨가 렌더링되지 않고 리터럴 문자로 노출되는 오류 방지.

### 주요 결정 사항
1. **AI 프롬프트 볼드 문법 규칙 강화 (`summarizer.py`)**:
   - `SUMMARY_PROMPT_TEMPLATE` 및 `PARTIAL_SUMMARY_PROMPT`에 `**` 시작 기호 바로 뒤와 닫는 기호 바로 앞 공백 금지 규칙(`**텍스트**` O, `** 텍스트**` X, `** 텍스트 **` X)과 닫는 기호 뒤 1칸 공백 지침 명시.
2. **후처리 함수 `ensure_bold_spacing` 콜백 기반 재설계 (`summarizer.py`)**:
   - 정규식 `(?<!\*)\*\*([^\n*]+?)\*\*(?!\*)([^\s\n*]?)` 패턴 매칭 콜백을 사용하여 볼드 내부의 양쪽 공백(`.strip()`)을 제거하여 시작/끝 공백 오류를 해결하고, 뒤따르는 문자/기호와의 공백(`**텍스트** :`)을 안전하게 자동 확보.
   - 한 줄 내 다중 볼드(`**A** , **B**`) 파싱 시 태그 오인식으로 인한 공백 오삽입 버그 원천 해결.
3. **기존 마크다운 파일 89개 일괄 보정 (`output/`)**:
   - `output/` 폴더 내 기존 마크다운 파일 89개를 전수 검사하여 볼드 공백 오류가 있던 80개 파일 일괄 보정 완료.
4. **단위 테스트 보강 및 검증 (`test_pdf_processor.py`)**:
   - 시작 공백(`** 텍스트**`), 양쪽 공백(`** 텍스트 **`), 닫는 공백, 한 줄 내 다중 볼드 복합 케이스, 코드 블록 보호 케이스 등 단위 테스트 전체 통과 확인.

### 수정한 파일
- `summarizer.py`: `ensure_bold_spacing` 함수 재설계, 프롬프트 템플릿 규칙 보강
- `test_pdf_processor.py`: 볼드 공백 및 한 줄 다중 볼드 단위 테스트 케이스 보강
- `output/` 하위 `*_review.md` 파일들: 볼드 공백 보정 일괄 적용
- `CHANGELOG.md`: 변경 내역 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (볼드 공백 정규화, Mermaid 가독성/문법, 시리즈 파싱, 북커버 추출 모두 PASS)

---

## [2026-08-26] - Mermaid 4대 구문 오류(Syntax Error) 원천 차단 & 가독성 최적화

### 변경 목적
- **Mermaid 4대 구문 오류 해결**: 
  1. 보이지 않는 웹 특수 공백(`\u00a0`)으로 인한 파서 에러
  2. `subgraph` 식별자에 한글/공백/콜론(`:`) 직접 작성으로 인한 파싱 에러
  3. 노드 및 라벨의 특수문자(`/`, `:`, `'`, `&`, `·`)에 큰따옴표(`"..."`) 누락으로 인한 기호 오인 에러
  4. 비표준 점선 화살표(`-.라벨.->`, `.- ... -.`)로 인한 구문 에러
- **Mermaid 가독성 저하 및 볼드 공백 해결**: 과도하게 가로로 넓어져 폰트가 쌀알처럼 축소되는 문제 및 마크다운 볼드(`** **`) 뒤 공백 누락 해결.

### 주요 결정 사항
1. **AI 프롬프트 Mermaid 4대 오류 방지 규칙 강화 (`summarizer.py`)**:
   - `SUMMARY_PROMPT_TEMPLATE`에 공백 규칙, `subgraph 영문ID ["표시명"]` 규칙, 노드 `ID["텍스트"]` 및 라벨 `-->|"텍스트"|` 큰따옴표 필수 규칙, 표준 연결선 문법 명시.
2. **후처리 함수 `optimize_mermaid_diagram` 4대 오류 정규식 자동 보정 (`summarizer.py`)**:
   - `\u00a0` $\rightarrow$ 일반 ASCII 공백 자동 치환
   - `subgraph` 식별자 공백/한글/콜론 $\rightarrow$ `subgraph sub_N ["..."]` 자동 변환
   - 노드 라벨 큰따옴표 누락 $\rightarrow$ `ID["..."]` 자동 래핑
   - 비표준 점선(`-.라벨.->`) $\rightarrow$ `-.->|"라벨"|` 및 파이프 라벨 따옴표 누락 자동 보정
   - `graph LR/RL` $\rightarrow$ 세로형 `graph TD` 전환 및 고시인성 테마(`primaryColor: #F0F7FF`, `primaryTextColor: #0F172A`, `lineColor: #334155`, `edgeLabelBackground: #FFFFFF`) 지시문 자동 적용
3. **기존 마크다운 파일 90개 일괄 보정 (`output/`)**:
   - `output/` 폴더 내 기존 마크다운 파일들의 Mermaid 다이어그램에 4대 오류 보정 및 고시인성 테마를 일괄 적용.
4. **단위 테스트 추가 및 검증 (`test_pdf_processor.py`)**:
   - 4대 오류 패턴, 고시인성 테마 및 복합 케이스에 대한 단위 테스트(`test_mermaid_optimization`) 전체 통과 확인.

### 수정한/생성한 파일
- `summarizer.py`: `optimize_mermaid_diagram` 정규식 보강, 프롬프트 지침 업데이트
- `test_pdf_processor.py`: Mermaid 4대 오류 자동 보정 단위 테스트 추가
- `CHANGELOG.md`: 변경 내역 갱신
- `output/` 하위 90개 `*_review.md` 파일: 문법 보정 및 폰트 최적화 일괄 적용

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과

---

## [2026-08-24] - README.md 전면 개편, .gitignore 추가 및 GitHub 저장소 동기화

### 변경 목적
- 무료 할당량 자동 폴백, 대용량 PDF 분할 요약, 북커버 공백 처리 등 최신 개선사항을 README.md에 반영하고 GitHub 원격 저장소(`https://github.com/ethanjoh/pdf_summary`)와 동기화.
- 보안을 위한 `.env` 및 대용량/출력 파일 제외용 `.gitignore` 설정.

### 주요 결정 사항
1. **`.gitignore` 생성**: API 키(`.env`), `output/`, `sample_pdfs/`, `__pycache__/` 등이 원격에 업로드되지 않도록 제외 규칙 설정.
2. **`README.md` 개편**:
   - 일일 무료 할당량 초과 시 자동 모델 폴백(`gemini-3.7-flash` → `gemini-3.6-flash` → `gemini-3.5-flash`) 기능 명시
   - 분당 토큰/요청 한도(RPM/TPM) 자동 대기 재시도 로직 설명
   - 대용량 PDF 1M 토큰 초과 시 PyMuPDF 자동 3등분 분할 및 통합 요약 파이프라인 설명
   - 공백 치환 북커버 파일명(`{title}_cover.jpg`) 및 마크다운 완료 도서 스마트 스킵 기능 안내
   - 최신 기술 스택 및 프로젝트 구조 가이드 보강
3. **GitHub 동기화**: `main` 브랜치 기준 원격 저장소 푸시 완료.

### 수정한/생성한 파일
- `.gitignore`: 신규 생성
- `README.md`: 최신 기능 가이드 및 문서화 전면 개편
- `CHANGELOG.md`: 변경 내역 추가

---

## [2026-08-24] - 대용량 PDF 토큰 초과 시 자동 분할 요약 기능 추가

### 변경 목적
- `Principles of Marketing` 등 대용량 PDF가 모델의 입력 토큰 한도(1,048,576)를 초과하여 `400 INVALID_ARGUMENT` 에러로 실패하는 문제 해결.
- 토큰 초과 감지 시 PDF를 3등분하여 파트별 요약 → 최종 통합 서평 자동 생성.

### 주요 결정 사항
1. **자동 감지**: `INVALID_ARGUMENT` + `token` 키워드로 토큰 초과 에러를 구분.
2. **분할 전략**: PyMuPDF로 PDF를 페이지 기준 3등분하여 임시 파일로 분할.
3. **2단계 요약**: 각 파트를 개별 API 호출로 부분 요약 → 부분 요약들을 통합하는 최종 API 호출.
4. **폐지 모델 대응**: `gemini-2.5-flash` 404 에러로 `gemini-3.6-flash`로 교체, 404 에러도 폴백 대상에 추가.

### 수정한 파일
- `pdf_processor.py`: `split_pdf_into_parts()` 함수 추가
- `summarizer.py`: `PARTIAL_SUMMARY_PROMPT`, `MERGE_SUMMARY_PROMPT` 상수 추가, `_summarize_chunked()` 메서드 추가, `summarize_series_to_markdown()`에 토큰 초과 자동 분할 로직 추가, `FALLBACK_MODELS`에서 `gemini-2.5-flash` → `gemini-3.6-flash` 교체

### 테스트 결과
- 양 파일 구문 검증(ast.parse) 통과

## [2026-08-24] - 무료 할당량 에러 시 대체 모델 자동 폴백 기능 추가

### 변경 목적
- `gemini-3.7-flash` 모델의 일일 무료 할당량(20회/일) 초과 시 무의미한 재시도 반복 대신, 대체 모델로 자동 전환하여 작업이 중단 없이 계속 진행되도록 개선.

### 주요 결정 사항
1. **에러 유형 구분**: 일일 할당량 초과(`PerDay`/`FreeTier`)와 분당 한도 초과(`RPM`/`TPM`)를 별도로 감지.
2. **대체 모델 폴백**: `FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]` 순서로 자동 전환하여 재시도.
3. **분당 한도 초과**: 기존과 동일하게 대기 후 재시도.
4. **모든 모델 소진 시**: 명확한 해결 방법 안내 메시지와 함께 종료.

### 수정한 파일
- `summarizer.py`: `FALLBACK_MODELS` 상수 추가, `_generate_content_with_retry()` 메서드에 에러 유형 구분 및 대체 모델 자동 폴백 로직 구현

### 테스트 결과
- 구문 검증(ast.parse) 통과

## [2026-08-23] - 버그 수정 (북커버 파일명 공백을 언더스코어로 치환하여 마크다운 이미지 링크 깨짐 방지)

### 변경 목적
- 도서명에 공백(스페이스)이 포함되어 있을 경우 생성된 북커버 이미지 파일명에 공백이 들어가 마크다운(`![북커버](./...)`)에서 링크가 끊어지거나 이미지가 표시되지 않는(엑박) 현상 해결.

### 주요 결정 사항
1. **북커버 파일명 공백 치환 (`main.py`)**:
   - `safe_cover_stem = title.replace(" ", "_")`를 적용하여 `{도서명_공백제거}_cover.jpg`로 저장하고 마크다운 본문 링크도 동일하게 연동.
2. **기존 파일 호환성 유지 (`main.py`)**:
   - 공백이 포함된 기존 커버 파일(`{title}_cover.jpg` 또는 `.png`)이 이미 존재하는 경우에도 스킵 조건을 정확히 인식하도록 다중 포맷 체크 적용.

### 수정한/생성한 파일
- `main.py`: 북커버 파일명 공백 치환 및 기존 파일 호환성 검사 보강
- `test_pdf_processor.py`: 공백 포함 도서명에 대한 북커버 공백 제거 및 파일 생성 단위 테스트 추가
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (`희망의_끈_cover.jpg` 공백 없는 파일명 생성 및 존재 확인)

---

## [2026-08-23] - 기능 개선 (입력 폴더명 기반 출력 서브폴더 자동 생성 및 분리 저장)

### 변경 목적
- 서로 다른 도서 폴더(예: 소설, 경제경영 등)를 일괄 처리할 때 `output` 디렉토리 아래에 불러온 입력 폴더명의 서브폴더를 자동 생성하여 결과물을 폴더별로 깔끔하게 분리 저장하도록 개선.

### 주요 결정 사항
1. **서브폴더 경로 자동 설정 (`main.py`)**:
   - `output_path = base_output_path / input_path.name`으로 지정하여 `output/{입력폴더명}/` 하위에 북커버와 마크다운이 저장되도록 처리.
   - 기존 완료 파일 검사(`find_existing_markdown`) 및 커버 이미지 검사도 해당 서브폴더 기준으로 정확히 연동.
2. **가이드 문서 동기화 (`README.md`)**:
   - `output/{입력폴더명}/` 출력 구조 설명 갱신.

### 수정한/생성한 파일
- `main.py`: 입력 폴더명 서브폴더 경로 구성 적용
- `README.md`: 산출물 경로 설명 갱신
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 정상 통과
- 경로 생성 및 기존 스킵 로직 검증 완료

---

## [2026-08-23] - 기능 개선 (문학 및 비문학 전 장르 맞춤형 AI 요약 프롬프트 고도화)

### 변경 목적
- 도서 장르가 소설/문학뿐만 아니라 경제경영, 과학/기술, 인문/사회, 자기계발 등 다양한 비문학 도서일 경우에도 결말/스포일러 없이 독서 욕구와 지적 호기심을 극대화하도록 요약 템플릿 전면 업그레이드.

### 주요 결정 사항
1. **장르별 자동 분기 지침 수립 (`summarizer.py`)**:
   - **소설/문학**: 사건의 발단, 인물들의 팽팽한 심리전 및 위기 상황을 영화 예고편처럼 생생하게 서술하되 결말/진범/반전 스포일러는 철저히 방지. 인물 관계도 Mermaid 다이어그램 제공.
   - **비문학 (경제/경영/과학/인문/자기계발)**: 저자의 핵심 문제의식, 시대적 통찰, 책 속의 놀라운 실제 사례/데이터/전략을 명쾌하게 풀어내고 '핵심 개념/프레임워크' 구조도 Mermaid 다이어그램 제공.
2. **독서 유도 Hook 섹션 강화**:
   - '독서 전 미리 보는 핵심 관전 포인트 / 질문 3가지' 섹션을 신설하여 책을 직접 읽고 싶어지게 만드는 강력한 호기심 유발.
3. **가이드 문서 동기화 (`README.md`)**:
   - 산출물 마크다운 구성 가이드 갱신.

### 수정한/생성한 파일
- `summarizer.py`: `SUMMARY_PROMPT_TEMPLATE` 장르 적응형으로 전면 개편
- `README.md`: 마크다운 구성 안내 갱신
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과

---

## [2026-08-22] - 기능 개선 (북커버 이미지를 고용량 PNG에서 경량 JPG 포맷으로 변경)

### 변경 목적
- 북커버 이미지 추출 시 수 MB에 달하던 PNG 용량을 경량 압축 JPG 포맷으로 전환하여 시각적 화질 손실 없이 파일 용량을 대폭(약 80% 이상) 절감하고 블로그 로딩 최적화.

### 주요 결정 사항
1. **북커버 기본 저장 포맷 JPG 전환 (`main.py`, `pdf_processor.py`)**:
   - 북커버 파일명을 `{도서명}_cover.jpg`로 변경하고 마크다운 본문 이미지 링크도 `.jpg`로 연동.
   - `extract_book_cover`에서 `.jpg` 저장 시 기본 퀄리티 90%(`jpg_quality=90`)를 적용하여 고화질 경량화 지원.
2. **기존 `.png` 커버 호환성 유지 (`main.py`)**:
   - 이미 기존에 `.png`로 생성된 커버 이미지가 있는 도서도 정상 인식하여 불필요한 재작업 방지.
3. **가이드 문서 동기화 (`README.md`)**:
   - 산출물 파일명 안내를 `_cover.jpg`로 갱신.

### 수정한/생성한 파일
- `pdf_processor.py`: `extract_book_cover`에 JPG 품질 파라미터 및 저장 처리 추가
- `main.py`: 북커버 확장자 `.jpg` 변경 및 `.png` 호환성 유지
- `test_pdf_processor.py`: `.jpg` 커버 캡처 단위 테스트 갱신
- `README.md`: 산출물 안내 갱신
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 정상 통과 (북커버 JPG 약 66KB 경량 생성 확인)

---

## [2026-08-22] - 기능 개선 (도서 간 기본 쿨다운 상향으로 429 한도 초과 예방 및 재시도 안내 메시지 개선)

### 변경 목적
- 대용량 PDF 도서 연속 처리 시 Gemini 무료 티어의 1분당 토큰 한도(TPM) 초과로 인한 429 에러 메시지 발생을 사전에 예방하고, 재시도 발생 시 안심할 수 있는 명확한 상태 안내로 변경.

### 주요 결정 사항
1. **도서 간 쿨다운 대기 시간 기본값 상향 (`main.py`, `README.md`)**:
   - `--delay` 기본값을 기존 `5.0초`에서 `35.0초`로 변경하여 1분 토큰 윈도우가 안전하게 리셋되도록 사전 예방.
2. **429 재시도 안내 메시지 톤앤매너 개선 (`summarizer.py`)**:
   - 경고/에러 표기(`[!] ⚠️`) 대신 `[*] ⏳ Gemini 무료 토큰 할당량(RPM/TPM) 리셋 대기 중...`으로 상태 안내 변경.

### 수정한/생성한 파일
- `main.py`: `--delay` 기본값 35.0으로 수정
- `summarizer.py`: 재시도 대기 로그 메시지 개선
- `README.md`: 옵션 테이블 기본값 갱신
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 정상 통과
- `python main.py --help` 기본값(35.0초) 반영 확인

---

## [2026-08-22] - 경고 개선 (Google GenAI AFC 자동 함수 호출 경고 메시지 억제)

### 변경 목적
- `google-genai` SDK에서 `generate_content` 호출 시 출력되던 불필요한 자동 함수 호출(AFC) 권장 경고 메시지(`Direct use of automatic function calling (AFC) in Models.generate_content is not recommended...`) 억제.

### 주요 결정 사항
1. **AFC 비활성화 명시적 설정 (`summarizer.py`)**:
   - `types.GenerateContentConfig(automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))`를 `generate_content` 호출 시 전달하여 불필요한 AFC 초기화를 방지.
2. **콘솔 경고 필터링 (`summarizer.py`)**:
   - `warnings.filterwarnings`로 관련 UserWarning 메시지를 필터링하여 깨끗한 콘솔 로그 유지.

### 수정한/생성한 파일
- `summarizer.py`: AFC disable config 및 warnings 필터 적용
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 정상 통과
- GenerateContentConfig 설정 유효성 검증 완료

---

## [2026-08-22] - 기능 개선 (순차 처리 파이프라인 안정화 및 단계별 로그 명확화)

### 변경 목적
- 도서 요약 작업 시 하나의 도서가 완전히 종료된 후 안전하게 다음 도서로 넘어가도록 순차 파이프라인 흐름을 명확히 하고, 오류 발생 시에도 쿨다운 대기를 보장하여 API 과부하 방지.

### 주요 결정 사항
1. **단계별 콘솔 로그 직관화 (`main.py`, `summarizer.py`)**:
   - `[1단계: 북커버]`, `[2단계: AI 분석]`으로 내부 단계를 명확히 분리하여 병렬 실행 오해 방지.
   - 도서 처리 완료 시 `[완료]` 메시지 및 다음 도서 진행 전 대기 상태를 명확히 출력.
2. **오류 발생 시에도 안전 쿨다운 대기 보장 (`main.py`)**:
   - 도서 처리 중 에러가 발생하더라도 `finally` 블록을 통해 다음 도서로 넘어가기 전 안전 쿨다운(`--delay`) 대기를 항상 수행하도록 수정.

### 수정한/생성한 파일
- `main.py`: 단계별 로그 개선 및 `finally` 쿨다운 대기 보장
- `summarizer.py`: Gemini 업로드/인덱싱 로그 포맷 정리
- `CHANGELOG.md`: 변경 사항 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 정상 통과
- CLI 도움말 및 실행 흐름 정상 확인

---

## [2026-08-22] - 버그 수정 (PDF 파일 중복 수집 및 단권 도서의 시리즈 오인식/중복 업로드 해결)

### 변경 목적
- Windows 환경에서 대소문자 미구분으로 인해 `.pdf`와 `.PDF` 파일 검색 시 동일한 파일이 2번씩 수집되어 단권 도서가 2권짜리 시리즈로 오인식되고 Gemini API에 2회 중복 업로드되던 문제 해결.

### 주요 결정 사항
1. **파일 수집 시 대소문자 무관 고유 파일 수집 (`main.py`)**:
   - `input_path.glob("*.pdf") + input_path.glob("*.PDF")` 방식에서 `iterdir()` 순회 및 `.suffix.lower() == ".pdf"` 기반 `Path.resolve()` 중복 제거 방식으로 변경.
2. **시리즈 그룹화 내 방어적 중복 제거 (`pdf_processor.py`)**:
   - `group_pdf_series` 함수에 전달된 파일 리스트에 중복 경로가 있더라도 `resolve()` 기준으로 사전 필터링하여 단권 도서가 시리즈로 오인식되는 현상 원천 차단.
3. **단위 테스트 및 회귀 방지 (`test_pdf_processor.py`)**:
   - 중복 파일 리스트 인입 시 단일 도서(`is_series=False`, 1권)로 정상 분류되는지 및 디렉토리 내 고유 파일 수집이 정확히 1개씩 이루어지는지 검증 테스트 추가.

### 수정한/생성한 파일
- `main.py`: PDF 파일 수집 시 중복 방지 로직 적용
- `pdf_processor.py`: `group_pdf_series` 내 중복 파일 제거 방어 코드 추가
- `test_pdf_processor.py`: 중복 파일 처리 및 파일 수집 단위 테스트 추가 및 테스트 환경 정리 로직 보강
- `CHANGELOG.md`: 수정 사항 및 테스트 결과 기록

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 전체 정상 통과 (시리즈 파싱, 1권 커버 추출, 스트림 업로드 헤더, 마크다운 스킵, 중복 방어, 고유 파일 수집 모두 PASS)
- `python main.py --help` CLI 도움말 정상 동작 확인

---

## [2026-08-16] - 기능 개선 (마크다운 생성 완료 도서 스마트 스킵 & 미완료 도서 선별 처리)

### 변경 목적
- 이미 마크다운 파일(`.md`)이 생성되어 있는 도서는 Gemini API 호출 및 불필요한 토큰 소모 없이 확실하게 건너뛰고(Skip), 생성되지 않은 파일만 선별하여 처리하도록 개선.

### 주요 결정 사항
1. **마크다운 완료 판별 정밀화 (`find_existing_markdown`)**:
   - 대표 마크다운(`{title}_review.md`) 및 개별 파일 마크다운의 존재 여부와 내용(0바이트 초과)을 확인.
   - 마크다운이 존재할 경우 AI 분석 호출을 즉시 스킵(Skip)하며, 북커버 이미지만 누락된 경우 로컬에서 즉시 캡처 후 안전하게 스킵.
2. **사전 완료 현황 통계 안내**:
   - 배치 작업 시작 전 전체 도서 중 완료된 도서(스킵 예정)와 신규 처리 대상 도서 수를 미리 집계하여 터미널에 명확히 안내.

### 수정한/생성한 파일
- `main.py`: `find_existing_markdown` 함수 추가 및 마크다운 파일 기준 스마트 스킵/사전 통계 로직 구현
- `test_pdf_processor.py`: 마크다운 파일 존재 시 스킵 대상 판별 단위 테스트 추가

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 실행 완료 (마크다운 스킵 판별 검증 통과)

---

## [2026-08-16] - 기능 개선 (1개 도서 완료 후 순차 처리 안정화 & 429 Rate Limit 자동 복구)

### 변경 목적
- 도서 요약 작업 시 분당 토큰/요청 한도(`429 RESOURCE_EXHAUSTED`)로 인한 중단을 방지하고, 1개 도서의 처리가 완전히 종료된 후 안전하게 다음 도서로 넘어가도록 순차 파이프라인 강화

### 주요 결정 사항
1. **429 Quota Exceeded 지능형 자동 대기 및 재시도**:
   - `summarizer.py`에 `_generate_content_with_retry` 구현.
   - API 응답의 권장 대기 시간(`retry in 40s`)을 자동 파싱하여 대기 후 최대 5회까지 작업 자동 재시도.
2. **도서 간 안전 쿨다운 딜레이 (`--delay`, 기본 5초)**:
   - 각 도서의 AI 요약 및 저장이 완료된 후 다음 도서로 넘어가기 전 안전 대기 시간을 두어 분당 토큰 누적 방지.
3. **완료 도서 자동 건너뛰기 (Skip / 이어하기 기능)**:
   - 이미 마크다운과 북커버가 존재하는 도서는 자동으로 건너뛰어(Skip), 중단 후 재실행 시에도 미완료 도서만 연속 처리 가능 (`--overwrite` 옵션으로 덮어쓰기 제어).

### 수정한/생성한 파일
- `summarizer.py`: `_generate_content_with_retry` 추가 및 API 호출 적용
- `main.py`: `--delay`, `--overwrite` CLI 인자 추가 및 순차 대기/스킵 로직 구현
- `README.md`: 신규 CLI 옵션 설명 갱신

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 정상 통과
- `main.py --help` CLI 인자 파서 검증 완료

---

## [2026-08-16] - 모델 업데이트 (Gemini 기본 모델을 최신 gemini-3.7-flash로 업그레이드)

### 변경 목적
- 구글 API에서 `gemini-2.5-flash` 모델 지원이 종료됨에 따라 발생하는 `404 NOT_FOUND` 오류 해결

### 주요 결정 사항
1. **최신 플래그십 Flash 모델 적용**: `summarizer.py` 및 `main.py`의 기본 모델명을 현재 최신 고속 모델인 `gemini-3.7-flash`로 변경.
2. **문서 및 가이드 동기화**: `README.md`의 CLI 옵션 기본값 안내 갱신.

### 수정한/생성한 파일
- `summarizer.py`: `PDFSummarizer`의 기본 `model_name`을 `gemini-3.7-flash`로 수정
- `main.py`: CLI `--model` 기본값을 `gemini-3.7-flash`로 수정
- `README.md`: 옵션 테이블 기본 모델명 반영

### 테스트 결과
- `main.py --help` 기본값 출력 검증 완료
- Gemini API 연동 테스트 정상 통과

---

## [2026-08-16] - 신규 기능 (시리즈 도서 자동 감지 및 1권 커버 추출 + 통합 요약 지원)

### 변경 목적
- `1, 2, 3권`, `(1), (2)`, `_01, _02`, `상/중/하`, `Vol.1` 등 시리즈물로 구성된 PDF 도서들을 자동 감지하여, 첫 번째 PDF(1권)에서만 북커버 이미지를 추출하고 전체 시리즈를 종합 요약하는 하나의 완성된 블로그 마크다운 문서를 생성하도록 개선.

### 주요 결정 사항
1. **시리즈 파일명 패턴 자동 감지 및 정렬**:
   - `pdf_processor.py`에 `parse_series_info` 및 `group_pdf_series` 함수 구현.
   - 다양한 시리즈 표기 패턴(숫자, 권/부/편, 괄호, 구분자, Vol, 상/중/하 등)을 정규식으로 분석하여 동일 기본 도서명 그룹으로 분류하고 1권부터 오름차순 정렬.
2. **첫 번째 PDF(1권) 북커버 단일 추출**:
   - 시리즈물 그룹의 1번째 파일(`first_file`)에서만 대표 북커버(`{도서명}_cover.png`)를 캡처하여 불필요한 중복 이미지 생성 방지.
3. **Gemini 멀티모달 다중 PDF 통합 요약**:
   - `summarizer.py`에 `summarize_series_to_markdown` 구현.
   - 시리즈 내 모든 PDF를 순차 업로드 후 `contents=[*uploaded_files, prompt]`로 전달하여 시리즈 전체 줄거리, 인물 관계, 매력 포인트를 관통하는 하나의 완성된 서평 포스팅(`{도서명}_review.md`) 생성.
4. **단일 도서 호환성 유지**:
   - 단권 도서는 기존과 동일하게 단독으로 1권 커버 및 단독 요약 마크다운 생성.

### 수정한/생성한 파일
- `pdf_processor.py`: `parse_series_info`, `group_pdf_series` 함수 추가
- `summarizer.py`: `summarize_series_to_markdown` 메서드 및 시리즈물 프롬프트 지침 추가
- `main.py`: 시리즈 그룹화 기반 배치 처리 및 1권 커버 추출 로직 적용
- `test_pdf_processor.py`: 다양한 시리즈 파일명 패턴 파싱, 그룹화/정렬 및 1권 커버 캡처 단위 테스트 추가
- `README.md`: 시리즈물 자동 감지 및 통합 요약 기능 설명 추가

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 실행 완료 (12가지 시리즈 패턴 파싱, 1/2/3권 정렬 및 1권 커버 추출 모두 PASS)
- `main.py --help` 실행 정상 확인

---

## [2026-08-16] - 버그 수정 (한글 파일명 PDF 업로드 시 ASCII 인코딩 에러 해결)

### 변경 목적
- 한글 파일명(예: `희망의 끈.pdf`)을 가진 PDF를 처리할 때 Gemini API 파일 업로드 과정에서 발생하는 `'ascii' codec can't encode characters` 예외 해결

### 주요 결정 사항
1. **바이너리 파일 스트림 업로드 전환**: `google-genai` SDK에 파일 경로 문자열 대신 `with open(pdf_path, 'rb') as f:` 파일 객체를 전달하도록 수정. 이를 통해 라이브러리 내부에서 HTTP 요청 헤더(`X-Goog-Upload-File-Name`)에 한글 문자열이 직접 들어가 발생하는 ASCII 인코딩 에러를 원천 방지.
2. **UTF-8 display_name 적용**: Gemini API 메타데이터로 안전한 전달을 위해 `config=dict(mime_type="application/pdf", display_name=pdf_path.name)` 설정 적용.

### 수정한/생성한 파일
- `summarizer.py`: `self.client.files.upload` 호출 방식을 파일 스트림 객체 전달 방식으로 변경
- `test_pdf_processor.py`: 한글 파일명(`희망의 끈.pdf`)에 대한 북커버 추출, 메타데이터 조회 및 스트림 업로드 헤더 유효성 검증 테스트 케이스 추가

### 테스트 결과
- `test_pdf_processor.py` 단위 테스트 실행 완료 (영문 및 한글 파일명 처리, 스트림 업로드 옵션 검증 모두 PASS)
- `main.py --help` 정상 동작 확인

---

## [2026-08-16] - 초기 버전 릴리즈 (PDF 도서 요약 & 블로그 마크다운 생성기)

### 변경 목적
- 특정 폴더 내 스캔된 PDF 도서들을 일괄 분석하여 북커버 캡처 이미지와 SEO/AEO 최적화 블로그용 마크다운(.md) 문서를 자동 생성하는 프로그램 구현 (수동 블로그 포스팅 용도)

### 주요 결정 사항
1. **북커버 이미지 추출**: PyMuPDF(`pymupdf`)를 사용하여 첫 페이지를 200 DPI의 고해상도 PNG 이미지로 저장.
2. **스캔 PDF 분석 및 요약 엔진**: Google Gemini API 최신 SDK(`google-genai`)를 활용해 OCR 없이도 대용량 멀티모달 PDF 파일을 직접 업로드 분석하도록 구현.
3. **스포일러 방지 가이드라인**: 프롬프트 엔지니어링을 통해 결말/반전 누설을 엄격히 차단하고, 도입부 및 흥미진진한 갈등 중심의 서술 유도.
4. **등장인물 관계도**: 텍스트 설명과 함께 마크다운 내 시각적 `Mermaid` 다이어그램(`graph TD/LR`) 자동 생성.
5. **SEO & AEO 최적화**: 메타 타이틀, 메타 디스크립션, 추천 태그 및 AI 검색 엔진(ChatGPT Search, Perplexity 등) 인용용 FAQ Q&A 섹션 템플릿 적용.

### 수정한/생성한 파일
- `pdf_processor.py`: 첫 페이지 북커버 캡처 및 PDF 메타데이터 추출 모듈
- `summarizer.py`: Gemini API 기반 스포일러 방지 요약 및 SEO/AEO 마크다운 생성 모듈
- `main.py`: CLI 인자 처리 및 폴더 내 PDF 일괄 배치 처리 메인 스크립트
- `requirements.txt`: 필수 패키지 정의 (`PyMuPDF`, `google-genai`, `python-dotenv`, `tqdm`)
- `.env.example`: 환경 변수 설정 템플릿
- `test_pdf_processor.py`: 북커버 추출 및 메타데이터 처리 단위 테스트
- `README.md`: 프로젝트 개요, 설치 및 실행 가이드

### 테스트 결과
- PyMuPDF 기반 1페이지 캡처 및 메타데이터 추출 단위 테스트 통과 (`test_pdf_processor.py` 정상 완료)
- CLI 인자 파서 및 도움말 출력 검증 완료 (`python main.py --help` 정상 동작)
