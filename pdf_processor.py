# PDF 파일의 첫 페이지 북커버 이미지 추출 및 문서 정보 처리를 담당하는 모듈
import os
import tempfile
from pathlib import Path
from typing import Dict, Any
import pymupdf


def extract_book_cover(
    pdf_path: str | Path,
    output_image_path: str | Path,
    dpi: int = 200,
    jpg_quality: int = 90
) -> str:
    """
    PDF의 첫 번째 페이지(북커버)를 고해상도 이미지(JPG/PNG)로 캡처하여 저장합니다.

    :param pdf_path: 대상 PDF 파일 경로
    :param output_image_path: 저장할 이미지 파일 경로 (확장자에 따라 자동 포맷 결정)
    :param dpi: 해상도 DPI (기본 200)
    :param jpg_quality: JPG 저장 시 화질 퀄리티 (1~100, 기본 90)
    :return: 저장된 이미지 파일의 절대 경로 문자열
    """
    pdf_path = Path(pdf_path)
    output_image_path = Path(output_image_path)
    
    # 출력 디렉토리 생성
    output_image_path.parent.mkdir(parents=True, exist_ok=True)

    # PDF 열기
    doc = pymupdf.open(pdf_path)
    if len(doc) == 0:
        raise ValueError(f"빈 PDF 파일입니다: {pdf_path}")

    # 첫 페이지 가져오기
    first_page = doc[0]
    
    # DPI 기반 렌더링 매트릭스 설정
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pix = first_page.get_pixmap(matrix=matrix, alpha=False)
    
    # 이미지 저장 (JPG 확장자인 경우 퀄리티 적용)
    if output_image_path.suffix.lower() in [".jpg", ".jpeg"]:
        pix.save(str(output_image_path), jpg_quality=jpg_quality)
    else:
        pix.save(str(output_image_path))
    doc.close()
    
    return str(output_image_path.resolve())


def get_pdf_metadata(pdf_path: str | Path) -> Dict[str, Any]:
    """
    PDF 파일의 기본 메타데이터 및 페이지 수를 반환합니다.
    """
    pdf_path = Path(pdf_path)
    doc = pymupdf.open(pdf_path)
    page_count = len(doc)
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    metadata = doc.metadata or {}
    doc.close()

    return {
        "file_name": pdf_path.name,
        "file_stem": pdf_path.stem,
        "page_count": page_count,
        "file_size_mb": round(file_size_mb, 2),
        "title": metadata.get("title", ""),
        "author": metadata.get("author", ""),
    }


def parse_series_info(stem: str) -> tuple[str, int]:
    """
    파일명(확장자 제외)에서 기본 도서명(base_title)과 시리즈 권수 순서 번호(volume_order)를 추출합니다.
    시리즈 패턴이 없을 경우 (stem, 0)을 반환합니다.

    :param stem: 확장자가 제거된 파일명
    :return: (기본 도서명, 권수 순서 번호)
    """
    import re
    clean_stem = stem.strip()

    # 1. 상, 중, 하 / 상권, 중권, 하권 패턴
    han_match = re.search(
        r"^(.*?)(?:[\s_.\-\(\[\{]+(?:제)?\s*([상중하])\s*(?:권|부|편)?[\)\]\}]?)$",
        clean_stem,
        re.IGNORECASE
    )
    if han_match and han_match.group(1).strip():
        order_map = {"상": 1, "중": 2, "하": 3}
        return han_match.group(1).strip(), order_map.get(han_match.group(2), 1)

    # 2. 숫자 기반 시리즈 패턴
    patterns = [
        # 1) 명시적 Vol / Volume / v 접두사 (예: ' Vol.1', '_vol2', ' v3', '-volume4')
        r"^(.*?)(?:[\s_.\-]+(?:vol(?:ume)?|v)\.?\s*(\d+)\s*(?:권|부|편|장)?)$",
        # 2) 괄호 형태: (1), [02], {3권}, (Vol.1), [제2권]
        r"^(.*?)(?:[\s_.\-]*[\(\[\{](?:vol(?:ume)?|v|제)?\s*(\d+)\s*(?:권|부|편|장)?[\)\]\}])$",
        # 3) 공백 + 제N권 / 숫자 + 권/부/편/장 (예: ' 1권', ' 1', ' 제2권', ' 1부')
        r"^(.*?)(?:\s+(?:제)?\s*(\d+)\s*(?:권|부|편|장)?)$",
        # 4) 구분자(_ 또는 -) + 숫자 (예: '_01', '-2', '_1권')
        r"^(.*?)(?:[_\-]+(?:제)?\s*(\d+)\s*(?:권|부|편|장)?)$",
        # 5) 접미어로 직접 붙은 경우 (예: '도서명1권', '도서명2부', '도서명Vol.1')
        r"^(.*?)(?:(?:vol(?:ume)?|v|제)\.?\s*(\d+)\s*(?:권|부|편|장)?)$",
        r"^(.*?)(?:(\d+)\s*(?:권|부|편))$",
    ]

    for pat in patterns:
        m = re.match(pat, clean_stem, re.IGNORECASE)
        if m and m.group(1).strip():
            base = m.group(1).strip()
            num = int(m.group(2))
            return base, num

    return clean_stem, 0


def group_pdf_series(pdf_files: list[Path]) -> list[Dict[str, Any]]:
    """
    PDF 파일 목록을 분석하여 단일 도서 및 시리즈 도서 그룹으로 분류하고
    각 그룹 내에서 권수 순서대로 정렬하여 반환합니다.

    :param pdf_files: Path 객체 리스트
    :return: 도서 그룹 정보 리스트 (title, is_series, file_count, files, first_file)
    """
    # 중복 파일 경로 제거 (resolve 기준)
    unique_pdf_files = list({Path(p).resolve(): Path(p) for p in pdf_files}.values())
    groups: Dict[str, list[tuple[int, Path]]] = {}

    for pdf_file in unique_pdf_files:
        base_title, vol_num = parse_series_info(pdf_file.stem)
        if base_title not in groups:
            groups[base_title] = []
        groups[base_title].append((vol_num, pdf_file))

    result = []
    for title, items in groups.items():
        # vol_num 기준 정렬, 같으면 파일명 기준 정렬
        sorted_items = sorted(items, key=lambda x: (x[0], x[1].name))
        files = [item[1] for item in sorted_items]
        is_series = len(files) > 1 or (len(files) == 1 and sorted_items[0][0] > 0)

        result.append({
            "title": title,
            "is_series": is_series,
            "file_count": len(files),
            "files": files,
            "first_file": files[0]
        })

    # 전체 도서 목록을 제목 순으로 정렬
    result.sort(key=lambda x: x["title"])
    return result


def split_pdf_into_parts(pdf_path: str | Path, num_parts: int = 2) -> list[Path]:
    """
    PDF 파일을 페이지 기준으로 균등 분할하여 임시 PDF 파일 리스트를 반환합니다.
    호출자가 사용 후 반환된 임시 파일들을 직접 삭제해야 합니다.

    :param pdf_path: 원본 PDF 파일 경로
    :param num_parts: 분할할 파트 수 (기본: 2)
    :return: 분할된 임시 PDF 파일 경로 리스트
    """
    pdf_path = Path(pdf_path)
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)

    if total_pages < num_parts:
        doc.close()
        return [pdf_path]

    pages_per_part = total_pages // num_parts
    parts = []

    for i in range(num_parts):
        start = i * pages_per_part
        end = (i + 1) * pages_per_part if i < num_parts - 1 else total_pages

        part_doc = pymupdf.open()
        part_doc.insert_pdf(doc, from_page=start, to_page=end - 1)

        tmp = tempfile.NamedTemporaryFile(
            suffix=".pdf", prefix=f"{pdf_path.stem}_part{i+1}_", delete=False
        )
        tmp.close()
        part_doc.save(tmp.name)
        part_doc.close()
        parts.append(Path(tmp.name))

    doc.close()
    return parts
