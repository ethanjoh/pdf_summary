# 스캔된 PDF 도서를 일괄 처리하여 북커버 이미지와 블로그용 마크다운을 생성하는 메인 실행 스크립트
import os
import sys
import warnings
import argparse
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

# pymupdf4llm 내부 레이아웃 연산 중 발생하는 런타임 경고 음소거
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*divide by zero.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, module=".*pymupdf.*")

from pdf_processor import extract_book_cover, get_pdf_metadata, group_pdf_series
from summarizer import PDFSummarizer, QuotaExhaustedError

# Windows 콘솔 utf-8 출력 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="스캔된 PDF 도서 일괄 분석 및 블로그용 마크다운/북커버 이미지 생성기"
    )
    parser.add_argument(
        "--input_dir", "-i",
        type=str,
        default=os.environ.get("DEFAULT_INPUT_DIR", "./sample_pdfs"),
        help="PDF 파일들이 위치한 입력 폴더 경로"
    )
    parser.add_argument(
        "--output_dir", "-o",
        type=str,
        default=os.environ.get("DEFAULT_OUTPUT_DIR", "./output"),
        help="결과물(마크다운 및 북커버 이미지)을 저장할 출력 폴더 경로"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="북커버 이미지 추출 해상도 DPI (기본값: 200)"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="gemini-3.7-flash",
        help="사용할 Gemini 모델명 (기본값: gemini-3.7-flash)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=35.0,
        help="도서 처리 완료 후 다음 도서 작업 전 안전 쿨다운 대기 시간(초) (기본값: 35.0)"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="이미 생성된 마크다운/커버 이미지가 있어도 건너뛰지 않고 다시 생성"
    )
    parser.add_argument(
        "--source", "-s",
        action="store_true",
        help="PDF에서 추출한 도서 원문 마크다운 파일({도서명}_source.md)을 함께 저장 (기본값: False)"
    )
    return parser.parse_args()


def find_existing_markdown(output_path: Path, title: str, files: list[Path]) -> Path | None:
    """
    대표 마크다운 파일({title}_review.md) 또는 개별 파일 마크다운이
    이미 생성되어 있고 비어있지 않은지(st_size > 0) 확인합니다.
    """
    primary_md = output_path / f"{title}_review.md"
    if primary_md.exists() and primary_md.stat().st_size > 0:
        return primary_md

    for f in files:
        alt_md = output_path / f"{f.stem}_review.md"
        if alt_md.exists() and alt_md.stat().st_size > 0:
            return alt_md

    return None


def main():
    import time
    # .env 파일 로드
    load_dotenv()

    args = parse_args()
    input_path = Path(args.input_dir).resolve()
    base_output_path = Path(args.output_dir).resolve()

    if not input_path.exists() or not input_path.is_dir():
        print(f"[!] 입력 폴더를 찾을 수 없습니다: {input_path}")
        print("입력 폴더를 생성하고 PDF 파일들을 넣어주세요.")
        sys.exit(1)

    # 입력 폴더명을 서브폴더명으로 사용하여 결과물 분리 저장
    output_path = base_output_path / input_path.name

    print("=" * 60)
    print(" [PDF 도서 요약 & 블로그 마크다운 생성기]")
    print(f" - 입력 폴더: {input_path}")
    print(f" - 출력 폴더: {output_path} (하위 서브폴더: '{input_path.name}')")
    print(f" - 사용할 모델: {args.model}")
    print(f" - 작업 간 대기 시간(쿨다운): {args.delay}초")
    print(f" - 기존 파일 덮어쓰기: {'활성화' if args.overwrite else '비활성화 (기존 마크다운 완료본 건너뜀)'}")
    print(f" - 소스 마크다운 저장: {'활성화' if args.source else '비활성화'}")
    print("=" * 60)

    # PDF 파일 목록 검색 (대소문자 무관 및 중복 방지)
    pdf_files = sorted(
        list({f.resolve(): f for f in input_path.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"}.values()),
        key=lambda p: p.name
    )
    if not pdf_files:
        print(f"[*] '{input_path}' 폴더에 PDF 파일이 없습니다.")
        sys.exit(0)

    output_path.mkdir(parents=True, exist_ok=True)

    # 도서 및 시리즈 그룹화
    books = group_pdf_series(pdf_files)
    series_count = sum(1 for b in books if b["is_series"])
    print(f"[*] 총 {len(pdf_files)}개의 PDF 파일 발견 -> {len(books)}종의 도서(시리즈 {series_count}건)로 분류 완료.")

    # 마크다운 완료 현황 사전 집계
    if not args.overwrite:
        already_completed = [b for b in books if find_existing_markdown(output_path, b["title"], b["files"]) is not None]
        pending_count = len(books) - len(already_completed)
        print(f"[*] 현황 분석: 전체 {len(books)}종 중 {len(already_completed)}종 완료(스킵 예정), [ {pending_count}종 ] 신규 처리 예정.\n")
    else:
        print(f"[*] 덮어쓰기 모드: 전체 {len(books)}종 모두 다시 처리합니다.\n")

    # API 키 확인 및 Summarizer 초기화
    try:
        summarizer = PDFSummarizer(model_name=args.model)
    except ValueError as e:
        print(f"[!] {e}")
        print("'.env' 파일을 열어 GEMINI_API_KEY를 설정한 후 다시 실행해 주세요.")
        sys.exit(1)

    success_count = 0
    skip_count = 0
    fail_count = 0
    quota_exhausted = False

    for idx, book in enumerate(tqdm(books, desc="도서 처리 진행률"), 1):
        title = book["title"]
        files = book["files"]
        first_file = book["first_file"]
        is_series = book["is_series"]

        # 마크다운 뷰어/웹에서 이미지 경로 공백으로 인한 링크 깨짐 방지를 위해 파일명 공백을 '_'로 치환
        safe_cover_stem = title.replace(" ", "_")
        cover_filename = f"{safe_cover_stem}_cover.jpg"
        cover_path = output_path / cover_filename
        md_filename = f"{title}_review.md"
        md_path = output_path / md_filename
        source_md_filename = f"{title}_source.md"
        source_md_path = output_path / source_md_filename

        # 이미 마크다운 파일이 생성되어 있는지 확인
        if not args.overwrite:
            existing_md = find_existing_markdown(output_path, title, files)
            if existing_md:
                # 마크다운은 있으나 북커버 이미지(.jpg 또는 .png)가 없는 경우 로컬에서 즉시 캡처(API 호출 없음)
                has_cover = (
                    cover_path.exists()
                    or (output_path / f"{safe_cover_stem}_cover.png").exists()
                    or (output_path / f"{title}_cover.jpg").exists()
                    or (output_path / f"{title}_cover.png").exists()
                )
                if not has_cover:
                    try:
                        extract_book_cover(first_file, cover_path, dpi=args.dpi)
                    except Exception:
                        pass
                print(f"\n>> [건너뛰기/SKIP] 이미 마크다운이 완료된 도서입니다: '{title}' ({existing_md.name})")
                skip_count += 1
                continue

        if is_series:
            file_names_str = ", ".join([f.name for f in files])
            print(f"\n>> [{idx}/{len(books)}] ▶ 도서 작업 시작: '{title}' (시리즈 총 {len(files)}권: {file_names_str})")
        else:
            print(f"\n>> [{idx}/{len(books)}] ▶ 도서 작업 시작: '{title}' ({first_file.name})")

        try:
            # 1. 1권(첫 번째 PDF) 북커버 이미지 추출
            print(f"   - [1단계: 북커버] 대표 북커버 이미지 추출 중... ('{first_file.name}')")
            extract_book_cover(first_file, cover_path, dpi=args.dpi)
            print(f"     [✓] 북커버 저장 완료: {cover_path.name}")

            # 2. AI 내용 분석 및 통합 마크다운 생성
            if is_series:
                print(f"   - [2단계: AI 분석] 시리즈 전체({len(files)}권) 마크다운 분석 및 서평 생성 중...")
            else:
                print(f"   - [2단계: AI 분석] 도서 마크다운 분석 및 서평 생성 중...")

            summarizer.summarize_series_to_markdown(
                pdf_paths=files,
                book_title=title,
                cover_image_filename=cover_filename,
                output_md_path=md_path,
                output_source_md_path=source_md_path,
                save_source=args.source
            )
            print(f"     [✓] 마크다운 리뷰 생성 완료: {md_path.name}")
            print(f"   [완료] '{title}' 도서 작업이 성공적으로 종료되었습니다.")
            success_count += 1

        except QuotaExhaustedError as e:
            print(f"\n   [!] 🛑 일일 무료 할당량 소진(또는 모든 모델 실패)으로 작업을 즉시 중단합니다.")
            print(f"       사유: {e}")
            fail_count += 1
            quota_exhausted = True
            break
        except Exception as e:
            print(f"   [!] '{title}' 처리 중 에러 발생: {e}")
            fail_count += 1

        finally:
            # 3. 도서 간 안전 쿨다운 대기 (할당량 소진 시 제외, 다음 도서 진행 전 쿼터 보호)
            if not quota_exhausted and idx < len(books) and args.delay > 0:
                print(f"   [*] 다음 도서 진행 전 안전 쿨다운 대기 중 ({args.delay}초)...")
                time.sleep(args.delay)

    print("\n" + "=" * 60)
    print(" [작업 완료 보고]")
    print(f" - 전체 대상 도서: {len(books)}종")
    print(f" - 신규 처리 성공: {success_count}건")
    if skip_count > 0:
        print(f" - 기존 완료 건너뜀: {skip_count}건")
    if fail_count > 0:
        print(f" - 실패: {fail_count}건")
    print(f" - 결과물 저장 위치: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
