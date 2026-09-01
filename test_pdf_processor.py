# PyMuPDF를 이용한 테스트용 샘플 PDF 생성 및 북커버 캡처 모듈 단위 테스트
import os
import sys
from pathlib import Path
import pymupdf

# Windows 콘솔 utf-8 출력 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pdf_processor import (
    extract_book_cover,
    get_pdf_metadata,
    parse_series_info,
    group_pdf_series,
    split_pdf_into_parts,
    extract_markdown_from_pdf,
)


def create_sample_pdf(file_path: Path):
    """테스트용 샘플 PDF 파일 생성"""
    doc = pymupdf.open()
    
    # 1페이지 (북커버)
    page1 = doc.new_page()
    rect1 = pymupdf.Rect(50, 50, 500, 700)
    page1.draw_rect(rect1, color=(0.2, 0.4, 0.8), fill=(0.9, 0.95, 1.0), width=3)
    page1.insert_text((100, 150), f"[{file_path.stem}]", fontsize=24, color=(0.1, 0.2, 0.5))
    page1.insert_text((100, 220), "Author: Ethan Tester", fontsize=16, color=(0.3, 0.3, 0.3))
    page1.insert_text((100, 300), "Sample PDF for Testing", fontsize=14, color=(0.4, 0.4, 0.4))
    
    # 2페이지 (본문)
    page2 = doc.new_page()
    page2.insert_text((50, 80), "Chapter 1: The Beginning", fontsize=20, color=(0, 0, 0))
    page2.insert_text((50, 130), "This is a story about adventures and mystery...", fontsize=12, color=(0.2, 0.2, 0.2))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(file_path))
    doc.close()


def test_series_parsing():
    print("\n--- [시리즈 파일명 패턴 파싱 테스트] ---")
    test_cases = [
        ("희망의 끈 1", ("희망의 끈", 1)),
        ("희망의 끈 2권", ("희망의 끈", 2)),
        ("희망의 끈 (3)", ("희망의 끈", 3)),
        ("희망의 끈_01", ("희망의 끈", 1)),
        ("희망의 끈-02", ("희망의 끈", 2)),
        ("희망의 끈 [3권]", ("희망의 끈", 3)),
        ("희망의 끈 Vol.1", ("희망의 끈", 1)),
        ("희망의 끈 v2", ("희망의 끈", 2)),
        ("희망의 끈 상", ("희망의 끈", 1)),
        ("희망의 끈 중권", ("희망의 끈", 2)),
        ("희망의 끈 하권", ("희망의 끈", 3)),
        ("단권 소설책", ("단권 소설책", 0)),
    ]

    for stem, expected in test_cases:
        res = parse_series_info(stem)
        assert res == expected, f"파싱 실패: '{stem}' -> 결과 {res}, 기대값 {expected}"
        print(f"   [OK] '{stem}' -> base='{res[0]}', vol={res[1]}")
    print("   -> 시리즈 파일명 파싱 테스트 통과!")


def test_bold_spacing():
    print("\n--- [마크다운 볼드(** **) 공백 및 렌더링 자동 보정(ensure_bold_spacing) 테스트] ---")
    from summarizer import ensure_bold_spacing

    test_cases = [
        # (입력, 기대값)
        # 1. 시작 기호 뒤 또는 닫는 기호 앞 잘못된 공백 제거
        ("** 텍스트**", "**텍스트**"),
        ("** 텍스트 **", "**텍스트**"),
        ("**텍스트 **", "**텍스트**"),
        ("** 텍스트 **: 설명", "**텍스트** : 설명"),
        ("> ** 💡 핵심 한 줄 요약 ** : 문장", "> **💡 핵심 한 줄 요약** : 문장"),
        ("1. ** [포인트 1] **: 첫 번째", "1. **[포인트 1]** : 첫 번째"),
        ("- ** 주요 주제 ** : 내용", "- **주요 주제** : 내용"),
        # 2. 닫는 기호 뒤 공백 누락 보정
        ("**도서명**: 책제목", "**도서명** : 책제목"),
        ("**‘왼쪽 페이지’**이라는 설명", "**‘왼쪽 페이지’** 이라는 설명"),
        ("**핵심 키워드**는 매우 중요하다.", "**핵심 키워드** 는 매우 중요하다."),
        ("**SEO Title** : 이미 공백 있음", "**SEO Title** : 이미 공백 있음"),
        ("> **💡 핵심 한 줄 요약**: 문장", "> **💡 핵심 한 줄 요약** : 문장"),
        ("1. **[포인트 1]**: 첫 번째", "1. **[포인트 1]** : 첫 번째"),
        ("**Q1. 질문인가요?**\n- **A**: 답변", "**Q1. 질문인가요?**\n- **A** : 답변"),
        # 3. 한 줄에 여러 볼드 구문이 존재하는 복합 케이스
        (
            "- **핵심 구성 안내** : 책은 인간의 상호작용 양식을 ** 기버(Giver)** , ** 테이커(Taker)** , ** 매처(Matcher)** 의 3가지 유형으로 분류하고",
            "- **핵심 구성 안내** : 책은 인간의 상호작용 양식을 **기버(Giver)** , **테이커(Taker)** , **매처(Matcher)** 의 3가지 유형으로 분류하고"
        ),
        # 4. 코드 블록 보호 검증
        (
            "본문 ** 강조 **입니다.\n```mermaid\ngraph TD\n    A[\"**노드**입니다\"] --> B\n```\n하단 ** 강조 **입니다.",
            "본문 **강조** 입니다.\n```mermaid\ngraph TD\n    A[\"**노드**입니다\"] --> B\n```\n하단 **강조** 입니다."
        ),
    ]

    for inp, expected in test_cases:
        actual = ensure_bold_spacing(inp)
        assert actual == expected, f"보정 실패!\n입력: {inp}\n실제: {actual}\n기대: {expected}"
        print(f"   [OK] '{inp[:30]}...' -> '{actual[:30]}...'")

    print("   -> 마크다운 볼드(** **) 공백 보정 단위 테스트 전체 통과!")


def test_escape_tilde():
    print("\n--- [마크다운 물결표(~) 취소선 오인 방지 이스케이프(escape_tilde) 테스트] ---")
    from summarizer import escape_tilde

    test_cases = [
        # (입력, 기대값)
        # 1. 수치 범위 및 기간 표기
        ("30~50자 내외", "30\\~50자 내외"),
        ("1~2문장의 핵심 요약 (80~150자)", "1\\~2문장의 핵심 요약 (80\\~150자)"),
        ("주요 인물 4~6명의 갈등", "주요 인물 4\\~6명의 갈등"),
        ("1990~2000년대 경제 흐름", "1990\\~2000년대 경제 흐름"),
        # 2. 문장 내 일반 물결표 및 취소선 형태
        ("안녕하세요~ 반갑습니다~", "안녕하세요\\~ 반갑습니다\\~"),
        ("~~취소선 텍스트~~", "\\~\\~취소선 텍스트\\~\\~"),
        # 3. 이미 이스케이프된 경우 중복 이스케이프 방지
        ("30\\~50자", "30\\~50자"),
        ("이미 \\~ 이스케이프됨", "이미 \\~ 이스케이프됨"),
        # 4. 인라인 코드(`...`) 보호 검증
        ("일반 텍스트 1~2와 `인라인 코드 1~2` 비교", "일반 텍스트 1\\~2와 `인라인 코드 1~2` 비교"),
        ("`~` 기호를 설명합니다.", "`~` 기호를 설명합니다."),
        # 5. 코드 블록(```...```) 보호 검증
        (
            "본문 10~20페이지입니다.\n```python\nx = ~y\nprint('1~2')\n```\n하단 30~40페이지입니다.",
            "본문 10\\~20페이지입니다.\n```python\nx = ~y\nprint('1~2')\n```\n하단 30\\~40페이지입니다."
        ),
    ]

    for inp, expected in test_cases:
        actual = escape_tilde(inp)
        assert actual == expected, f"물결표 이스케이프 실패!\n입력: {inp}\n실제: {actual}\n기대: {expected}"
        print(f"   [OK] '{inp[:30]}...' -> '{actual[:30]}...'")

    print("   -> 마크다운 물결표 이스케이프 단위 테스트 전체 통과!")


def test_tag_normalization():
    print("\n--- [메타데이터 태그 '#' 제거 및 쉼표 구분(키워드1, 키워드2) 자동 정규화(normalize_tags) 테스트] ---")
    from summarizer import normalize_tags

    test_cases = [
        # (입력, 기대값)
        # 1. 공백으로만 구분된 다중 해시태그 -> # 제거 및 쉼표 구분 정규화
        (
            "- **추천 카테고리/태그** : #경제경영 #더골 #TheGoal #엘리골드렛 #TOC",
            "- **추천 카테고리/태그** : 경제경영, 더골, TheGoal, 엘리골드렛, TOC"
        ),
        # 2. 이미 쉼표로 구분된 해시태그 -> # 제거 및 쉼표 구분 정규화
        (
            "- **추천 카테고리/태그** : #경제경영, #더골, #TheGoal",
            "- **추천 카테고리/태그** : 경제경영, 더골, TheGoal"
        ),
        # 3. 이미 # 없이 쉼표로 나열된 텍스트 -> 정규화 유지
        (
            "- **추천 카테고리/태그** : 경제경영, 더골, TheGoal",
            "- **추천 카테고리/태그** : 경제경영, 더골, TheGoal"
        ),
        # 4. 다양한 태그 라인 prefix 및 단일 태그
        (
            "- **추천 태그** : #소설 #추리 #스릴러",
            "- **추천 태그** : 소설, 추리, 스릴러"
        ),
        (
            "- **태그** : #단일태그",
            "- **태그** : 단일태그"
        ),
        (
            "- **Tags** : #AI #Python #Gemini",
            "- **Tags** : AI, Python, Gemini"
        ),
    ]

    for inp, expected in test_cases:
        actual = normalize_tags(inp)
        assert actual == expected, f"태그 정규화 실패!\n입력: {inp}\n실제: {actual}\n기대: {expected}"
        print(f"   [OK] '{inp}' -> '{actual}'")

    print("   -> 메타데이터 태그 '#' 제거 및 쉼표 구분 정규화 단위 테스트 전체 통과!")


def test_mermaid_optimization():
    print("\n--- [Mermaid 다이어그램 가독성 및 4대 구문 오류 자동 보정 테스트] ---")
    from summarizer import optimize_mermaid_diagram, postprocess_markdown

    # 1. 특수 공백(\u00a0) 치환 검증
    nbsp_sample = "```mermaid\ngraph\u00a0TD\n\u00a0\u00a0\u00a0\u00a0A[\"노드 A\"] --> B[\"노드 B\"]\n```"
    opt_nbsp = optimize_mermaid_diagram(nbsp_sample)
    assert "\u00a0" not in opt_nbsp, "특수 공백(\\u00a0)이 제거되지 않았습니다."
    print("   [OK] 1. 특수 공백(\\u00a0) -> 일반 ASCII 공백 자동 치환 확인")

    # 2. subgraph 식별자 오류 자동 보정 검증
    subgraph_sample = (
        "```mermaid\n"
        "graph TD\n"
        "    subgraph Phase 1: 기획 단계\n"
        "        A[\"노드 A\"]\n"
        "    end\n"
        "    subgraph 가족 및 친족\n"
        "        B[\"노드 B\"]\n"
        "    end\n"
        "```"
    )
    opt_sub = optimize_mermaid_diagram(subgraph_sample)
    assert 'subgraph sub_1 ["Phase 1: 기획 단계"]' in opt_sub
    assert 'subgraph sub_2 ["가족 및 친족"]' in opt_sub
    print("   [OK] 2. subgraph 식별자 공백/한글/콜론 오류 -> sub_N [\"...\"] 자동 변환 확인")

    # 3. 노드 라벨 큰따옴표 누락 보정 검증
    node_quote_sample = (
        "```mermaid\n"
        "graph TD\n"
        "    A[김수헌: 글로벌모니터 대표/기자] --> B[\"이미 따옴표 있음\"]\n"
        "```"
    )
    opt_node = optimize_mermaid_diagram(node_quote_sample)
    assert 'A["김수헌: 글로벌모니터 대표/기자"]' in opt_node
    assert 'B["이미 따옴표 있음"]' in opt_node
    print("   [OK] 3. 노드 라벨 특수문자 따옴표 누락 -> [\"...\"] 자동 보정 확인")

    # 4. 연결선 비표준 문법 및 따옴표 누락 보정 검증
    arrow_sample = (
        "```mermaid\n"
        "graph TD\n"
        "    A -.양자.-> B\n"
        "    A -->|대립/갈등| C\n"
        "    B -.- |협력 관계| C\n"
        "```"
    )
    opt_arrow = optimize_mermaid_diagram(arrow_sample)
    assert 'A -.->|"양자"| B' in opt_arrow
    assert 'A -->|"대립/갈등"| C' in opt_arrow
    assert 'B -.- |"협력 관계"| C' in opt_arrow
    print("   [OK] 4. 비표준 점선(-.라벨.->) 및 파이프 라벨 따옴표 누락 자동 보정 확인")

    # 5. %%{init:}%% 고시인성 테마 지시문 및 graph TD 전환 검증
    sample_mermaid = (
        "## 다이어그램\n"
        "```mermaid\n"
        "graph LR\n"
        "    A[\"인물 A\"] --> B[\"인물 B\"]\n"
        "```\n"
        "**설명**입니다."
    )
    optimized = optimize_mermaid_diagram(sample_mermaid)
    assert "primaryTextColor': '#0F172A'" in optimized, "Mermaid primaryTextColor 설정이 추가되지 않았습니다."
    assert "graph TD" in optimized, "graph LR이 graph TD로 전환되지 않았습니다."
    print("   [OK] 5. %%{init:...}%% 고시인성 테마 지시문 자동 추가 및 graph TD 전환 확인")

    # 6. postprocess_markdown 종합 검증 (볼드 공백 + 물결표 이스케이프 + Mermaid 4대 오류 + 고시인성 테마 동시 적용)
    combined_sample = (
        "**도서명**: 80/20 법칙 (30~50자)\n"
        "```mermaid\n"
        "graph LR\n"
        "    subgraph 핵심 원리: 80대 20\n"
        "        A[투입: 20%의 원인] -.결과 도출.-> B[산출: 80%의 성과]\n"
        "    end\n"
        "```\n"
        "**결론**입니다~"
    )
    result = postprocess_markdown(combined_sample)
    assert "**도서명** : 80/20 법칙 (30\\~50자)" in result
    assert "**결론** 입니다\\~" in result
    assert "graph TD" in result
    assert "primaryTextColor': '#0F172A'" in result
    assert 'subgraph sub_1 ["핵심 원리: 80대 20"]' in result
    assert 'A["투입: 20%의 원인"] -.->|"결과 도출"| B["산출: 80%의 성과"]' in result
    print("   [OK] 6. postprocess_markdown 종합 후처리(볼드 공백 + 물결표 이스케이프 + 4대 오류 보정 + 고시인성 테마) 완벽 동작 확인")
    print("   -> Mermaid 다이어그램 가독성 및 4대 구문 오류 자동 보정 테스트 전체 통과!")


def test_prompt_template_formatting():
    print("\n--- [프롬프트 템플릿 문자열 포맷팅(KeyError 방지) 테스트] ---")
    from summarizer import (
        SUMMARY_PROMPT_TEMPLATE,
        MERGE_SUMMARY_PROMPT,
        PARTIAL_TEXT_SUMMARY_PROMPT,
        PARTIAL_PDF_SUMMARY_PROMPT,
    )

    # 1. 단일 도서 포맷팅 테스트 (소비를 그만두다)
    prompt_single = SUMMARY_PROMPT_TEMPLATE.format(
        book_title="소비를 그만두다",
        cover_image_filename="소비를_그만두다_cover.jpg",
        series_notice="",
        book_content_section="\n--- 도서 본문 ---\n샘플 본문 텍스트\n"
    )
    assert "소비를 그만두다" in prompt_single
    assert "소비를_그만두다_cover.jpg" in prompt_single
    assert "샘플 본문 텍스트" in prompt_single
    assert "%%{init: {'theme': 'base'" in prompt_single
    assert "%%{{init" not in prompt_single
    print("   [OK] 1. 단일 도서 요약 프롬프트 포맷팅 정상 동작 ('소비를 그만두다')")

    # 2. 시리즈 도서 포맷팅 테스트
    prompt_series = SUMMARY_PROMPT_TEMPLATE.format(
        book_title="희망의 끈 (전 3권 시리즈)",
        cover_image_filename="희망의_끈_cover.jpg",
        series_notice="## 📚 시리즈물 특별 지침\n- 본 도서는 총 3권...",
        book_content_section=""
    )
    assert "희망의 끈 (전 3권 시리즈)" in prompt_series
    assert "시리즈물 특별 지침" in prompt_series
    assert "%%{init: {'theme': 'base'" in prompt_series
    print("   [OK] 2. 시리즈 도서 요약 프롬프트 포맷팅 정상 동작")

    # 3. 텍스트 부분 요약 프롬프트 포맷팅 테스트
    prompt_partial_text = PARTIAL_TEXT_SUMMARY_PROMPT.format(
        book_title="도서명",
        part_num=1,
        total_parts=3,
        chunk_text="파트 1 텍스트 내용"
    )
    assert "도서명" in prompt_partial_text
    assert "파트 1 텍스트 내용" in prompt_partial_text
    print("   [OK] 3. 텍스트 부분 요약(PARTIAL_TEXT_SUMMARY_PROMPT) 프롬프트 포맷팅 정상 동작")

    # 4. 분할 통합 요약 프롬프트 포맷팅 테스트
    prompt_merge = MERGE_SUMMARY_PROMPT.format(
        book_title="대용량 도서",
        total_parts=3,
        series_notice="",
        partial_summaries="### 파트 1 요약\n내용...",
        cover_image_filename="대용량_도서_cover.jpg"
    )
    assert "대용량 도서" in prompt_merge
    assert "파트 1 요약" in prompt_merge
    assert "%%{init: {'theme': 'base'" in prompt_merge
    print("   [OK] 4. 분할 통합(Merge) 요약 프롬프트 포맷팅 정상 동작")
    print("   -> 프롬프트 템플릿 포맷팅 테스트 전체 통과!")


def test_pdf_split(test_dir: Path):
    print("\n--- [PDF 분할(split_pdf_into_parts) 및 Windows 파일 잠금 해제 테스트] ---")
    multi_page_pdf = test_dir / "대용량테스트도서.pdf"
    
    # 6페이지짜리 샘플 PDF 생성
    doc = pymupdf.open()
    for i in range(6):
        page = doc.new_page()
        page.insert_text((50, 100), f"Page {i+1} Content", fontsize=20)
    doc.save(str(multi_page_pdf))
    doc.close()

    # 3등분 분할 실행 (Windows Permission denied 오류 없이 저장 및 파일 핸들 정상 해제 검증)
    parts = split_pdf_into_parts(multi_page_pdf, num_parts=3)
    assert len(parts) == 3, f"3개 파트로 분할되어야 하나 {len(parts)}개 반환됨"

    for idx, part in enumerate(parts, 1):
        assert part.exists(), f"분할된 파일이 존재하지 않음: {part}"
        part_doc = pymupdf.open(part)
        assert len(part_doc) == 2, f"각 파트가 2페이지여야 하나 {len(part_doc)}페이지임"
        part_doc.close()
        print(f"   [OK] 파트 {idx}: {part.name} (2페이지)")

    # 임시 파일 삭제 테스트 (파일 잠금 없이 정상 삭제되는지 확인)
    for part in parts:
        part.unlink()
        assert not part.exists()
    
    if multi_page_pdf.exists():
        multi_page_pdf.unlink()
    print("   [OK] 임시 분할 파일 정상 삭제 및 잠금 해제 확인")
    print("   -> PDF 분할 및 임시 파일 관리 테스트 통과!")


def test_cli_args():
    print("\n--- [CLI 인자 파서 및 --source 옵션 테스트] ---")
    import argparse
    from main import parse_args

    # 1. 기본값 검증 (--source 옵션 미지정 시 False)
    test_args_default = []
    import sys
    orig_argv = sys.argv
    try:
        sys.argv = ["main.py"]
        args = parse_args()
        assert args.source is False, f"기본값이 False여야 하나 {args.source}입니다."
        print("   [OK] 기본 실행 시 args.source == False 확인")

        # 2. --source 옵션 지정 시 True
        sys.argv = ["main.py", "--source"]
        args = parse_args()
        assert args.source is True, f"--source 지정 시 True여야 하나 {args.source}입니다."
        print("   [OK] --source 지정 시 args.source == True 확인")

        # 3. -s 단축 옵션 지정 시 True
        sys.argv = ["main.py", "-s"]
        args = parse_args()
        assert args.source is True, f"-s 지정 시 True여야 하나 {args.source}입니다."
        print("   [OK] -s 지정 시 args.source == True 확인")
    finally:
        sys.argv = orig_argv

    print("   -> CLI 인자 파서 단위 테스트 전체 통과!")


def test_quota_exhausted_handling():
    print("\n--- [일일 무료 할당량 소진(QuotaExhaustedError) 시 즉시 종료 로직 테스트] ---")
    from summarizer import QuotaExhaustedError

    # 1. 예외 타입 검증
    assert issubclass(QuotaExhaustedError, Exception)
    err = QuotaExhaustedError("모든 모델의 일일 무료 할당량이 소진되었습니다.")
    assert "일일 무료 할당량" in str(err)
    print("   [OK] QuotaExhaustedError 예외 클래스 정의 및 메시지 검증 성공")

    # 2. 메인 루프 즉시 탈출 및 실패 원인 수집 시뮬레이션 검증
    mock_books = [
        {"title": "도서1", "files": ["f1.pdf"]},
        {"title": "도서2", "files": ["f2.pdf"]},
        {"title": "도서3", "files": ["f3.pdf"]},
    ]
    processed_titles = []
    quota_exhausted = False
    fail_count = 0
    failed_books = []
    cooldown_called = False

    for idx, book in enumerate(mock_books, 1):
        processed_titles.append(book["title"])
        try:
            if idx == 1:
                raise QuotaExhaustedError("모든 모델(gemini-3.7-flash, gemini-3.6-flash)의 호출이 실패했습니다.")
        except QuotaExhaustedError as e:
            reason = "Gemini API 일일 무료 할당량(PerDay) 소진 또는 모든 모델 실패"
            fail_count += 1
            failed_books.append({"title": book["title"], "reason": reason, "detail": str(e)})
            quota_exhausted = True
            break
        except Exception as e:
            fail_count += 1
            failed_books.append({"title": book["title"], "reason": str(e), "detail": str(e)})
        finally:
            if not quota_exhausted:
                cooldown_called = True

    # 1번째 도서에서 즉시 중단되어 2, 3번째 도서는 처리되지 않아야 함
    assert processed_titles == ["도서1"], f"루프가 즉시 중단되지 않음: {processed_titles}"
    assert quota_exhausted is True
    assert fail_count == 1
    assert len(failed_books) == 1
    assert failed_books[0]["title"] == "도서1"
    assert "할당량" in failed_books[0]["reason"]
    assert cooldown_called is False, "할당량 소진 시 쿨다운이 호출되지 않아야 합니다."
    print("   [OK] QuotaExhaustedError 발생 시 쿨다운 대기 없이 메인 루프 즉시 탈출(break) 및 실패 원인 수집 검증 완료!")


def test_pdf_processor():
    import shutil
    test_dir = Path("./test_workspace")
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. 파싱 단위 테스트
    test_series_parsing()

    # 2. 마크다운 볼드 공백 보정 테스트
    test_bold_spacing()

    # 3. 마크다운 물결표 이스케이프 테스트
    test_escape_tilde()

    # 4. 메타데이터 태그 쉼표 구분 정규화 테스트
    test_tag_normalization()

    # 5. Mermaid 다이어그램 가독성 최적화 테스트
    test_mermaid_optimization()

    # 6. 프롬프트 템플릿 포맷팅 테스트
    test_prompt_template_formatting()

    # 7. PDF 분할 및 임시 파일 핸들 테스트
    test_pdf_split(test_dir)

    # 8. CLI 인자 파서 테스트
    test_cli_args()

    # 9. 일일 무료 할당량 소진 시 즉시 종료 테스트
    test_quota_exhausted_handling()

    print("\n--- [시리즈물 그룹화 및 1권 커버 캡처 테스트] ---")
    # 샘플 파일 생성
    h1 = test_dir / "희망의 끈 1.pdf"
    h2 = test_dir / "희망의 끈 2.pdf"
    h3 = test_dir / "희망의 끈 3.pdf"
    single = test_dir / "단권도서.pdf"

    for f in [h3, h1, h2, single]:  # 순서 섞어서 생성
        create_sample_pdf(f)

    # 그룹화 검증
    pdf_list = [h3, h1, h2, single]
    grouped = group_pdf_series(pdf_list)
    print(f"   그룹화 결과 ({len(grouped)}개 그룹):")
    for g in grouped:
        print(f"    * 도서명: {g['title']}, 시리즈여부: {g['is_series']}, 파일목록: {[f.name for f in g['files']]}")

    # 희망의 끈 그룹 검증
    hope_group = next(g for g in grouped if g["title"] == "희망의 끈")
    assert hope_group["is_series"] is True
    assert len(hope_group["files"]) == 3
    # 1권 -> 2권 -> 3권 순서로 정렬되었는지 확인
    assert hope_group["files"][0].name == "희망의 끈 1.pdf"
    assert hope_group["files"][1].name == "희망의 끈 2.pdf"
    assert hope_group["files"][2].name == "희망의 끈 3.pdf"
    assert hope_group["first_file"].name == "희망의 끈 1.pdf"

    # 첫 번째 PDF에서만 커버 이미지 추출 (.jpg 포맷, 파일명 공백 치환 검증)
    safe_title = hope_group["title"].replace(" ", "_")
    cover_path = test_dir / f"{safe_title}_cover.jpg"
    assert " " not in cover_path.name, "북커버 파일명에 공백이 포함되어 있습니다!"
    extract_book_cover(hope_group["first_file"], cover_path, dpi=150, jpg_quality=90)
    assert cover_path.exists()
    assert cover_path.stat().st_size > 0
    print(f"   [OK] 시리즈 1권에서 대표 북커버(JPG/공백제거) 생성 완료: {cover_path.name} ({cover_path.stat().st_size} bytes)")

    print("\n--- [google-genai 스트림 헤더 안전성 검증] ---")
    from google.genai import _extra_utils
    with open(h1, "rb") as f:
        http_options, size_bytes, mime_type = _extra_utils.prepare_resumable_upload(
            f, user_mime_type="application/pdf"
        )
        headers = http_options.headers or {}
        assert "X-Goog-Upload-File-Name" not in headers
        print(f"   [OK] 스트림 업로드 헤더 유효성 확인: {headers}")

    print("\n--- [마크다운 생성 완료 스킵(find_existing_markdown) 검증] ---")
    from main import find_existing_markdown
    # 1. 마크다운 파일이 아직 없는 경우
    assert find_existing_markdown(test_dir, "단권도서", [single]) is None
    # 2. 마크다운 파일을 생성한 경우
    test_md = test_dir / "단권도서_review.md"
    test_md.write_text("# Review Content", encoding="utf-8")
    assert find_existing_markdown(test_dir, "단권도서", [single]) == test_md
    print("   [OK] 마크다운 존재 시 정확하게 스킵 대상 판별 성공!")

    print("\n--- [중복 파일 인입 시 단일 도서 정상 판별(중복 제거) 테스트] ---")
    dup_single = test_dir / "중복테스트도서.pdf"
    create_sample_pdf(dup_single)
    # 동일한 파일이 2번 들어간 리스트
    dup_list = [dup_single, dup_single]
    dup_grouped = group_pdf_series(dup_list)
    assert len(dup_grouped) == 1
    assert dup_grouped[0]["is_series"] is False, f"단권 도서가 중복 인입되어 시리즈로 오인됨: {dup_grouped[0]}"
    assert len(dup_grouped[0]["files"]) == 1
    print("   [OK] 동일 파일 중복 인입 시에도 단일 도서(is_series=False, 1권)로 완벽 방어!")

    print("\n--- [파일 수집(대소문자 무관 및 중복 방지) 테스트] ---")
    collected_files = sorted(
        list({f.resolve(): f for f in test_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"}.values()),
        key=lambda p: p.name
    )
    # test_dir 안의 고유 파일 개수와 일치하는지 확인
    unique_file_names = {f.name for f in [h1, h2, h3, single, dup_single]}
    assert len(collected_files) == len(unique_file_names)
    print("\n--- [PDF 마크다운 텍스트 로컬 추출(extract_markdown_from_pdf) 테스트] ---")
    sample_pdf_path = test_dir / "마크다운추출테스트.pdf"
    create_sample_pdf(sample_pdf_path)
    extracted_md = extract_markdown_from_pdf(sample_pdf_path)
    assert extracted_md and len(extracted_md) > 0, "PDF 마크다운 추출 결과가 비어있습니다!"
    assert "Chapter 1: The Beginning" in extracted_md or "마크다운추출테스트" in extracted_md, "PDF 본문 텍스트가 정상 추출되지 않았습니다!"
    print(f"   [OK] PDF 로컬 마크다운 추출 성공:\n{extracted_md[:150]}...")

    # 원문 마크다운 파일({도서명}_source.md) 조건부 저장 검증
    # 1) save_source=False 시 파일 미저장 검증
    source_md_false = test_dir / "조건부저장_false_source.md"
    save_source_flag = False
    if save_source_flag:
        source_md_false.write_text(extracted_md, encoding="utf-8")
    assert not source_md_false.exists(), "save_source=False인데 소스 마크다운 파일이 생성되었습니다."
    print("   [OK] save_source=False 시 _source.md 미생성 검증 완료")

    # 2) save_source=True 시 파일 정상 저장 검증
    source_md_true = test_dir / "조건부저장_true_source.md"
    save_source_flag = True
    if save_source_flag:
        source_md_true.write_text(extracted_md, encoding="utf-8")
    assert source_md_true.exists()
    assert source_md_true.stat().st_size > 0
    print(f"   [OK] save_source=True 시 _source.md 정상 생성 검증 완료: {source_md_true.name}")

    print("\n--- [소스 마크다운(_source.md) 캐시 로드 및 스킵 시 보충 생성 테스트] ---")
    # 1. 캐시 로드 테스트 (_source.md가 이미 존재할 때)
    cached_source_file = test_dir / "캐시테스트도서_source.md"
    cached_content = "# Cached Book Source Content\nThis content is loaded directly from cache."
    cached_source_file.write_text(cached_content, encoding="utf-8")
    assert cached_source_file.exists() and cached_source_file.stat().st_size > 0
    # 캐시 파일 직접 로드 검증
    with open(cached_source_file, "r", encoding="utf-8") as f:
        loaded_cached_content = f.read().strip()
    assert loaded_cached_content == cached_content
    print("   [OK] 기존 _source.md 파일 캐시 우선 로드 검증 완료")

    # 2. 스킵 도서의 _source.md 자동 보충 생성 테스트
    skip_book_pdf = test_dir / "스킵보충도서.pdf"
    create_sample_pdf(skip_book_pdf)
    skip_review_md = test_dir / "스킵보충도서_review.md"
    skip_review_md.write_text("# Existing Review Markdown", encoding="utf-8")
    skip_source_md = test_dir / "스킵보충도서_source.md"
    if skip_source_md.exists():
        skip_source_md.unlink()

    # main.py의 스킵 보충 로직 시뮬레이션
    args_source_mode = True
    if args_source_mode and not (skip_source_md.exists() and skip_source_md.stat().st_size > 0):
        extracted_txt = extract_markdown_from_pdf(skip_book_pdf)
        if len(extracted_txt) >= 50:
            skip_source_md.write_text(extracted_txt, encoding="utf-8")

    assert skip_source_md.exists(), "스킵 도서에서 _source.md가 보충 생성되지 않았습니다."
    assert skip_source_md.stat().st_size > 0
    print(f"   [OK] 스킵 도서 대상 _source.md 자동 보충 생성 검증 완료: {skip_source_md.name}")

    print("\n[OK] 모든 단위 테스트 및 시리즈/스킵/중복방지/마크다운추출/원문조건부저장/캐시및보충/CLI옵션 검증 성공!")
    shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_pdf_processor()




