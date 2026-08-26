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

from pdf_processor import extract_book_cover, get_pdf_metadata, parse_series_info, group_pdf_series


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

    # 6. postprocess_markdown 종합 검증 (볼드 공백 + Mermaid 4대 오류 + 고시인성 테마 동시 적용)
    combined_sample = (
        "**도서명**: 80/20 법칙\n"
        "```mermaid\n"
        "graph LR\n"
        "    subgraph 핵심 원리: 80대 20\n"
        "        A[투입: 20%의 원인] -.결과 도출.-> B[산출: 80%의 성과]\n"
        "    end\n"
        "```\n"
        "**결론**입니다."
    )
    result = postprocess_markdown(combined_sample)
    assert "**도서명** : 80/20 법칙" in result
    assert "**결론** 입니다." in result
    assert "graph TD" in result
    assert "primaryTextColor': '#0F172A'" in result
    assert 'subgraph sub_1 ["핵심 원리: 80대 20"]' in result
    assert 'A["투입: 20%의 원인"] -.->|"결과 도출"| B["산출: 80%의 성과"]' in result
    print("   [OK] 6. postprocess_markdown 종합 후처리(볼드 공백 + 4대 오류 보정 + 고시인성 테마) 완벽 동작 확인")
    print("   -> Mermaid 다이어그램 가독성 및 4대 구문 오류 자동 보정 테스트 전체 통과!")


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

    # 3. Mermaid 다이어그램 가독성 최적화 테스트
    test_mermaid_optimization()

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
    print(f"   [OK] 폴더 내 {len(collected_files)}개 고유 PDF 파일 정확하게 수집 완료 (중복 없음)!")

    print("\n[OK] 모든 단위 테스트 및 시리즈/스킵/중복방지 검증 성공!")
    shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_pdf_processor()



