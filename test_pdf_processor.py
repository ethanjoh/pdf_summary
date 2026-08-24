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


def test_pdf_processor():
    import shutil
    test_dir = Path("./test_workspace")
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. 파싱 단위 테스트
    test_series_parsing()

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



