# CHANGELOG

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
