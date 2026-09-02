# Google Gemini API를 활용하여 PDF 도서를 분석하고 SEO/AEO 최적화 블로그 마크다운 포스팅을 생성하는 모듈
import os
import time
import warnings
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from pdf_processor import split_pdf_into_parts, extract_markdown_from_pdf

# SDK 내부 AFC(Automatic Function Calling) 권장 경고 메시지 필터링
warnings.filterwarnings("ignore", message=".*automatic function calling.*")
warnings.filterwarnings("ignore", message=".*AFC.*")

import re

# 일일 무료 할당량 초과 시 순서대로 시도할 대체 모델 목록
FALLBACK_MODELS = ["gemini-3.6-flash"]


class QuotaExhaustedError(Exception):
    """Gemini API의 일일 무료 할당량(PerDay/FreeTier) 소진 또는 모든 대체 모델 호출 실패 시 발생하는 예외"""
    pass


def ensure_bold_spacing(text: str) -> str:
    """
    마크다운 코드 블록(```...```)을 제외한 본문 영역에서
    1) 볼드 강조(**) 내부의 앞/뒤 잘못된 공백을 제거하여 정규화합니다.
       (예: ** 텍스트** -> **텍스트**, ** 텍스트 ** -> **텍스트**)
    2) **강조** 구문 뒤에 공백이나 줄바꿈 없이 글자나 기호가 바로 붙어 있는 경우
       한 칸 공백을 삽입하여 마크다운 렌더러에서 볼드 스타일이 정상 렌더링되도록 보정합니다.
       (예: **도서명**: -> **도서명** :, **'원칙'**이라는 -> **'원칙'** 이라는)
    """
    if not text:
        return ""

    # 코드 블록(```...```)과 일반 마크다운 텍스트 분리
    parts = text.split("```")
    pattern = re.compile(r'(?<!\*)\*\*([^\n*]+?)\*\*(?!\*)([^\s\n*]?)')

    def fix_bold_match(match):
        content = match.group(1).strip()
        if not content:
            return match.group(0)
        after = match.group(2)
        if after:
            return f"**{content}** {after}"
        return f"**{content}**"

    for i in range(0, len(parts), 2):  # 짝수 인덱스는 일반 텍스트 영역
        parts[i] = pattern.sub(fix_bold_match, parts[i])
    return "```".join(parts)


def escape_tilde(text: str) -> str:
    """
    마크다운 렌더러(티스토리, 네이버 블로그, 벨로그, 깃허브 등)에서
    물결표(~) 기호가 취소선(strikethrough)이나 특수 태그로 오인되어 서식이 깨지는 것을 방지합니다.
    - 코드 블록(```...```) 및 인라인 코드(`...`) 내부의 ~는 보호(유지)
    - 일반 텍스트 영역에서 이스케이프되지 않은 ~를 \\~ 형태로 치환 (이미 \\~인 경우 중복 이스케이프 방지)
    """
    if not text:
        return ""

    # 1. 코드 블록(```...```)과 일반 마크다운 텍스트 분리
    code_block_parts = text.split("```")
    for i in range(0, len(code_block_parts), 2):
        # 2. 인라인 코드(`...`) 분리
        inline_parts = code_block_parts[i].split("`")
        for j in range(0, len(inline_parts), 2):
            # 일반 텍스트 영역: 앞글자가 백슬래시(\)가 아닌 물결표(~)를 \~ 로 치환
            inline_parts[j] = re.sub(r'(?<!\\)~', r'\~', inline_parts[j])
        code_block_parts[i] = "`".join(inline_parts)
    return "```".join(code_block_parts)


def normalize_tags(text: str) -> str:
    """
    마크다운 메타데이터의 태그 라인에서 '#' 기호를 제거하고,
    블로그 플랫폼(티스토리, 네이버 블로그, 워드프레스, 벨로그 등) 태그 입력창에
    바로 복사하여 개별 태그로 자동 등록될 수 있도록 쉼표(`, `)로 구분된 순수 키워드 형태로 정규화합니다.
    예: #경제경영 #더골 #TOC -> 경제경영, 더골, TOC
        #경제경영, #더골, #TOC -> 경제경영, 더골, TOC
    """
    if not text:
        return ""

    def fix_tag_line(match):
        prefix = match.group(1)
        content = match.group(2)
        # #으로 시작하는 태그들이 있는 경우 #을 제거하여 추출
        tags = re.findall(r'#([^\s,#]+)', content)
        if tags:
            return f"{prefix}{', '.join(tags)}"
        # 이미 #이 없는 텍스트인 경우 쉼표 분리 정규화
        parts = [p.strip().lstrip('#') for p in content.split(',') if p.strip()]
        if parts:
            return f"{prefix}{', '.join(parts)}"
        return match.group(0)

    pattern = re.compile(
        r'^(.*?\*\*[^\n*]*(?:카테고리|태그|Tag|tag)[^\n*]*\*\*\s*:\s*)(.+)$',
        re.MULTILINE | re.IGNORECASE
    )
    return pattern.sub(fix_tag_line, text)


# Mermaid 고시인성(High-Contrast) 라이트 테마 설정 상수
MERMAID_HIGH_CONTRAST_INIT = (
    "%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#F0F7FF', "
    "'primaryTextColor': '#0F172A', 'primaryBorderColor': '#2563EB', 'lineColor': '#334155', "
    "'secondaryColor': '#FEF3C7', 'tertiaryColor': '#F0FDF4', 'edgeLabelBackground': '#FFFFFF', 'fontSize': '14px'}}}%%"
)


def optimize_mermaid_diagram(text: str) -> str:
    """
    마크다운 내 ```mermaid 코드 블록의 문법 오류를 방지하고 시인성을 최적화합니다:
    1. 보이지 않는 특수 공백(\u00a0 등)을 일반 공백으로 치환
    2. 가로로 비대해져 글씨가 축소되는 것을 막기 위해 graph LR/RL을 graph TD로 전환
    3. subgraph 식별자 오류 자동 보정: `subgraph Phase 1: 시작` -> `subgraph sub_1 ["Phase 1: 시작"]`
    4. 노드 라벨 큰따옴표 누락 보정: `ID[내용: 설명]` -> `ID["내용: 설명"]`
    5. 연결선(화살표) 비표준 문법 및 따옴표 누락 자동 보정:
       - `-.라벨.->` -> `-.->|"라벨"|`
       - `-->|라벨|` -> `-->|"라벨"|`
       - `-.->|라벨|` -> `-.->|"라벨"|`
       - `-.- |라벨|` -> `-.- |"라벨"|`
    6. 고시인성(소프트 배경 + 진한 다크 텍스트 #0F172A) 테마 지시문 자동 적용
    """
    if not text:
        return ""

    # 1. 특수 공백 치환
    text = text.replace('\u00a0', ' ')

    def fix_mermaid_block(match):
        block = match.group(1).strip()
        lines = block.split("\n")
        new_lines = []
        subgraph_counter = 1

        for line in lines:
            stripped = line.strip()

            # (1) graph LR / graph RL -> graph TD 변환
            if stripped.startswith("graph LR") or stripped.startswith("graph RL") or stripped.startswith("flowchart LR") or stripped.startswith("flowchart RL"):
                line = re.sub(r'(graph|flowchart)\s+(LR|RL)', r'\1 TD', line)
                new_lines.append(line)
                continue

            # (2) subgraph 식별자 오류 자동 보정
            m_sub = re.match(r'^(\s*subgraph\s+)(.+)$', line, re.IGNORECASE)
            if m_sub:
                prefix = m_sub.group(1)
                rest = m_sub.group(2).strip()
                # 이미 올바른 영문ID ["..."] 형태인 경우
                if re.match(r'^[a-zA-Z0-9_]+\s*\["[^"\n]+"\]$', rest):
                    new_lines.append(line)
                # 영문ID [라벨] (따옴표 누락) 형태인 경우: 예) Chapter_Flow [프레임워크]
                elif re.match(r'^([a-zA-Z0-9_]+)\s*\[([^"\n]+)\]$', rest):
                    m_label = re.match(r'^([a-zA-Z0-9_]+)\s*\[([^"\n]+)\]$', rest)
                    new_lines.append(f'{prefix}{m_label.group(1)} ["{m_label.group(2).strip()}"]')
                # 식별자 자체에 공백이나 특수문자가 들어간 경우: 예) Phase 1: 기획 또는 가족 및 친족
                else:
                    clean_label = rest.strip(' "\'[]')
                    new_lines.append(f'{prefix}sub_{subgraph_counter} ["{clean_label}"]')
                    subgraph_counter += 1
                continue

            # (3) 연결선(화살표) 비표준 문법 및 따옴표 보정
            # 비표준 점선 라벨: -.라벨.-> -> -.->|"라벨"|
            line = re.sub(r'-\.([^"\n\-]+?)\.->', r'-.->|"\1"|', line)
            # 비표준 무방향 점선: .- 라벨 -. 또는 -.- "라벨" -.- -> -.- |"라벨"|
            line = re.sub(r'\.-\s*([^"\n\-]+?)\s*-\.', r'-.- |"\1"|', line)
            line = re.sub(r'-\.-\s*"([^"\n]+?)"\s*-\.-', r'-.- |"\1"|', line)
            # 파이프 라벨 내 따옴표 누락 보정: -->|라벨| -> -->|"라벨"|
            line = re.sub(r'(-->|-\.->|-\.-\s*)\|(?!")([^|\n]+?)(?<!")\|', r'\1|"\2"|', line)

            # (4) 노드 라벨 따옴표 누락 보정: ID[텍스트] -> ID["텍스트"]
            # 단, 이미 ["..."] 형태가 아닌 경우만 변환
            line = re.sub(r'(\b[a-zA-Z0-9_]+\s*)\[(?!")([^\[\]\n]+?)(?<!")\]', r'\1["\2"]', line)

            new_lines.append(line)

        joined = "\n".join(new_lines)
        # (5) 고시인성 테마 지시문 확인 및 교체/추가
        if re.search(r'%%\s*\{\s*init\s*:.*?%%', joined, re.DOTALL | re.IGNORECASE):
            joined = re.sub(r'%%\s*\{\s*init\s*:.*?%%\n?', f"{MERMAID_HIGH_CONTRAST_INIT}\n", joined, flags=re.DOTALL | re.IGNORECASE)
        else:
            joined = f"{MERMAID_HIGH_CONTRAST_INIT}\n{joined}"

        return f"```mermaid\n{joined}\n```"

    return re.sub(r'```mermaid\s*\n([\s\S]*?)\n```', fix_mermaid_block, text)


def postprocess_markdown(text: str) -> str:
    """
    생성된 마크다운 본문의 렌더링 최적화를 위한 종합 후처리 함수:
    - 볼드(** **) 강조 구문 뒤 공백 자동 보정
    - 물결표(~) 취소선 오작동 방지 이스케이프(\\~) 자동 보정
    - 메타데이터 추천 태그 라인 쉼표 구분(#태그1, #태그2) 정규화
    - Mermaid 다이어그램 고시인성 테마(밝은 배경 + 진한 글씨) 및 세로형(TD) 구조 최적화
    - Mermaid 4대 구문 오류(특수공백, subgraph 식별자, 따옴표 누락, 비표준 연결선) 자동 보정
    """
    if not text:
        return ""
    text = ensure_bold_spacing(text)
    text = escape_tilde(text)
    text = normalize_tags(text)
    text = optimize_mermaid_diagram(text)
    return text


SUMMARY_PROMPT_TEMPLATE = """
당신은 베스트셀러 도서 전문 서평가이자 독서 마케팅 및 SEO/AEO(검색 및 AI 엔진 최적화) 전문가입니다.
제공된 도서 내용을 깊이 있게 분석한 후, 독자들이 책을 당장 구매하거나 펼쳐보고 싶어지도록 유도하는 최고 품질의 블로그 리뷰/서평 마크다운 포스팅을 작성해 주세요.
{series_notice}
{book_content_section}

## 🎯 도서 장르별 맞춤 분석 지침 (필독)
도서의 성격(소설/문학 vs 경제경영/과학/인문/자기계발 등 비문학)을 스스로 판단하여, 각 장르의 매력을 극대화하는 맞춤형 구성을 적용하세요.

1. **[소설 / 이야기 / 문학 도서의 경우]**
   - **줄거리 & 서스펜스** : 단순 요약이 아니라 영화 예고편처럼 사건의 발단, 인물들의 팽팽한 대립과 심리전, 위기 상황을 생생하고 흡입력 있게 서술하세요.
   - **스포일러 엄격 금지** : 결말, 최종 범인/진실, 핵심 반전은 절대로 누설하지 마세요. 클라이맥스 직전의 최고조 긴장감 상태에서 강렬한 의문과 여운을 남겨야 합니다.
   - **시각화 (인물 관계도)** : 이야기의 핵심 축을 이루는 주요 인물 4\\~6명의 갈등/협력 관계를 보여주는 세로형(graph TD) Mermaid 다이어그램 작성. (모든 조연을 나열하지 말고 핵심 대립 구도에 집중)

2. **[경제경영 / 과학 / 인문 / 자기계발 / 실용서 등 비문학 도서의 경우]**
   - **핵심 통찰 & 문제의식** : 저자가 던지는 시대적 화두와 문제의식, 기존 상식을 뒤흔드는 혁신적 아이디어/이론을 명쾌하고 흥미진진하게 제시하세요.
   - **풍부한 사례 & 프레임워크** : 책 속의 흥미로운 실제 사례, 과학적 발견, 비즈니스 전략이나 핵심 실행 원리를 독자의 지적 호기심을 자극하도록 서술하세요.
   - **시각화 (핵심 프레임워크)** : 책의 핵심 4\\~6개 이론 구조 또는 단계별 실행 프로세스를 보여주는 세로형(graph TD) Mermaid 다이어그램 작성.

---

## 📌 출력 형식 요구사항 (Markdown 포맷)

아래 마크다운 구조를 정확히 준수하여 작성해 주세요.
※ [마크다운 및 Mermaid 필수 문법 규칙 (오류 방지 및 고시인성 필독)]
1. **강조 구문 문법 & 공백 (필독)** : 굵은 글씨(**강조 텍스트**) 작성 시 ** 시작 기호 바로 뒤와 닫는 기호 바로 앞에는 공백을 절대 넣지 마세요 (**텍스트** O, ** 텍스트** X, ** 텍스트 ** X). 닫는 ** 뒤에는 다음 문자나 기호와의 구분을 위해 반드시 한 칸 공백을 넣으세요. (예: **핵심 통찰** 은 O, **도서명** : O)
2. **물결표 이스케이프 (필독)** : 마크다운 렌더러에서 물결표(~)가 취소선(strikethrough)으로 인식되는 오류를 방지하기 위해, 수치 범위(예: 30\\~50자, 1\\~2문장, 4\\~6명)나 물결 기호 사용 시 반드시 백슬래시를 붙여 \\~ 형태로 작성해주세요.
3. **태그 구분 (필독)** : 추천 카테고리/태그 작성 시 블로그 플랫폼(티스토리, 네이버, 워드프레스 등) 태그창에 바로 붙여넣을 수 있도록 '#' 기호 없이 쉼표(`,`)로 키워드를 구분하여 작성하세요. (예: 장르, 키워드1, 키워드2, 추천독자층)
4. **Mermaid 4대 구문 오류 방지 규칙 (Syntax Error 방지)** :
   - ① **특수 공백 금지** : 일반 ASCII 공백만 사용하세요. (웹 특수 공백 \\u00a0 절대 금지)
   - ② **subgraph 식별자** : 반드시 `subgraph 영문ID ["표시할 이름"]` 형식을 사용하세요. 식별자 자체에 한글, 공백, 콜론(:), 앰퍼샌드(&), 대괄호([])를 직접 쓰면 구문 오류가 발생합니다. (예: `subgraph SUB1 ["가족 및 친족"]`)
   - ③ **노드 & 라벨 큰따옴표 필수** : 특수문자(/, :, ', &, ·, 줄바꿈 태그)로 인한 파서 충돌을 막기 위해 노드는 반드시 `ID["텍스트"]`, 화살표 라벨은 `-->|"텍스트"|`처럼 큰따옴표로 감싸세요.
   - ④ **표준 연결선 문법** : 실선 화살표 `A -->|"라벨"| B`, 점선 화살표 `A -.->|"라벨"| B` (비표준 `-.라벨.->` 금지), 무방향 점선 `A -.- |"라벨"| B`를 준수하세요.
5. **Mermaid 고시인성 테마 & 가독성** : 세로형(`graph TD`), 핵심 노드 5\\~7개 이내 압축, 관계 라벨 2\\~4자 축약, 맨 윗줄 고시인성 테마 지시문 필수 선언:
   `%%{{init: {{'theme': 'base', 'themeVariables': {{'primaryColor': '#F0F7FF', 'primaryTextColor': '#0F172A', 'primaryBorderColor': '#2563EB', 'lineColor': '#334155', 'secondaryColor': '#FEF3C7', 'tertiaryColor': '#F0FDF4', 'edgeLabelBackground': '#FFFFFF', 'fontSize': '14px'}}}}}}%%`

---

### [메타데이터 및 SEO 요약]
- **SEO Title** : [클릭과 검색 유입을 극대화하는 매력적인 헤드라인 (30\\~50자 내외)]
- **Meta Description** : [검색엔진 및 AI 요약에 노출될 1\\~2문장의 핵심 요약 (80\\~150자)]
- **추천 카테고리/태그** : [장르], [핵심키워드1], [핵심키워드2], [추천독자층]

---

# [블로그 포스팅 메인 제목 (호기심과 지적 욕구를 자극하는 강력한 헤드라인)]

![{book_title} 북커버](./{cover_image_filename})

> **💡 핵심 한 줄 요약** : [이 책이 전하는 가장 강력한 메시지나 흥미로운 테마를 한눈에 보여주는 문장]

## 1. 📖 도서 개요 및 이 책이 주목받는 이유
- **도서명** : {book_title}
- **저자/역자** : [저자명 및 저자의 대표적 전문성/이력]
- **장르/분야** : [예: 경제경영 / 뇌과학 / 미스터리 스릴러 / 인문교양 / 자기계발 등]
- **이 책을 반드시 읽어야 하는 이유 / 첫인상** : [독자의 호기심과 읽고 싶은 욕구를 단번에 사로잡는 강력한 도입부 글]

## 2. 🧩 핵심 구조 및 시각적 다이어그램 (Mermaid Diagram)
- **핵심 구성 안내** : [소설인 경우 '주요 등장인물 관계', 비문학인 경우 '핵심 이론/개념 체계도' 요약]
- **Mermaid 다이어그램 (고시인성 세로형 구조)** :
```mermaid
%%{{init: {{'theme': 'base', 'themeVariables': {{'primaryColor': '#F0F7FF', 'primaryTextColor': '#0F172A', 'primaryBorderColor': '#2563EB', 'lineColor': '#334155', 'secondaryColor': '#FEF3C7', 'tertiaryColor': '#F0FDF4', 'edgeLabelBackground': '#FFFFFF', 'fontSize': '14px'}}}}}}%%
graph TD
    A["핵심 주체/인물 A"] -->|"갈등"| B["대립 대상/인물 B"]
    A -->|"협력"| C["조력자 C"]
    B -->|"추적"| D["수사관 D"]
```

## 3. 💡 핵심 내용 & 흥미진진한 탐구 (※ 스포일러 없음!)
- **이야기의 시작 / 저자의 핵심 질문 (도입)** : 사건의 발단 또는 저자가 제기하는 충격적인 문제의식
- **고조되는 갈등 / 핵심 이론과 흥미로운 사례 (전개)** :
  - (소설) 주인공이 마주하는 거대한 사건, 딜레마, 숨 막히는 전개
  - (비문학) 현실을 바꾸는 핵심 통찰, 저자의 독창적 논리와 놀라운 실제 사례/데이터
- **독자의 궁금증을 자극하는 결정적 순간** : 결말을 밝히지 않고 독자가 직접 책을 펼치게 만드는 흥미진진한 질문이나 미해결 과제 제시

## 4. 🔍 독서 전 미리 보는 핵심 관전 포인트 / 질문 3가지
> 책을 읽으며 독자가 직접 발견하고 생각해보게 만드는 강력한 호기심 유발 포인트입니다.
1. **[포인트 1]** : [핵심 질문 또는 주목할 장면/이론]
2. **[포인트 2]** : [핵심 질문 또는 주목할 장면/이론]
3. **[포인트 3]** : [핵심 질문 또는 주목할 장면/이론]

## 5. ✨ 이 책의 독보적 매력 & 추천 대상
- **독보적 매력 포인트 3가지** :
  - 1) [매력 1]
  - 2) [매력 2]
  - 3) [매력 3]
- **이런 분들께 강력 추천합니다** :
  - [ ] [구체적 추천 대상 1: 예 - 복잡한 경제 흐름 속 인사이트를 얻고 싶은 투자자/기획자]
  - [ ] [구체적 추천 대상 2: 예 - 뇌과학과 인간 행동 심리에 관심이 많은 분]
  - [ ] [구체적 추천 대상 3: 예 - 흡입력 있는 스토리와 반전을 즐기는 독자]

## 6. ❓ 자주 묻는 질문 (AEO 최적화 Q&A / FAQ)
> AI 검색 엔진(ChatGPT Search, Perplexity 등) 및 검색 사용자가 자주 묻는 핵심 질문에 대한 명쾌한 답변입니다.
 
**Q1. {book_title}은 어떤 책이며 누구에게 가장 큰 도움이 되나요?**
- **A** : [명확하고 설득력 있는 답변]

**Q2. 비전공자나 일반 독자도 쉽게 읽을 수 있는 난이도인가요?**
- **A** : [독서 난이도, 분량, 가독성에 대한 친절한 답변]

**Q3. 이 책만의 가장 독창적인 통찰(또는 차별점)은 무엇인가요?**
- **A** : [타 도서와의 결정적 차별점 제시]

---
"""

PARTIAL_TEXT_SUMMARY_PROMPT = """
당신은 도서 분석 전문가입니다. 아래 내용은 도서 '{book_title}'의 파트 {part_num}/{total_parts} 본문 텍스트입니다.
이 파트의 핵심 내용을 상세히 분석하여 다음 항목을 정리해 주세요:
- 주요 주제/논점/스토리 전개
- 핵심 인물, 개념, 이론, 사례
- 중요한 인용구나 데이터
- 전체 맥락에서 이 파트가 담당하는 역할

--- 파트 {part_num}/{total_parts} 본문 시작 ---
{chunk_text}
--- 파트 {part_num}/{total_parts} 본문 끝 ---

결과를 마크다운으로 작성해 주세요. 이 요약은 이후 전체 도서 서평 작성의 재료로 사용됩니다.
※ 마크다운 작성 시 **강조** 시작 기호 뒤나 닫는 기호 앞에는 공백을 넣지 말고(**텍스트**), 닫는 기호 뒤에는 반드시 한 칸 공백을 넣어주세요. (예: **주요 주제** :)
수치 범위나 물결표 사용 시에는 취소선 오작동 방지를 위해 반드시 백슬래시를 붙여 \\~ 형태로 작성해주세요. (예: 1\\~2페이지, 1990\\~2000년대)
"""

PARTIAL_PDF_SUMMARY_PROMPT = """
당신은 도서 분석 전문가입니다. 이 PDF는 하나의 도서를 분할한 파트 {part_num}/{total_parts}입니다.
이 파트의 핵심 내용을 상세히 분석하여 다음 항목을 정리해 주세요:
- 주요 주제/논점/스토리 전개
- 핵심 인물, 개념, 이론, 사례
- 중요한 인용구나 데이터
- 전체 맥락에서 이 파트가 담당하는 역할

결과를 마크다운으로 작성해 주세요. 이 요약은 이후 전체 도서 서평 작성의 재료로 사용됩니다.
※ 마크다운 작성 시 **강조** 시작 기호 뒤나 닫는 기호 앞에는 공백을 넣지 말고(**텍스트**), 닫는 기호 뒤에는 반드시 한 칸 공백을 넣어주세요. (예: **주요 주제** :)
수치 범위나 물결표 사용 시에는 취소선 오작동 방지를 위해 반드시 백슬래시를 붙여 \\~ 형태로 작성해주세요. (예: 1\\~2페이지, 1990\\~2000년대)
"""

MERGE_SUMMARY_PROMPT = """
당신은 베스트셀러 도서 전문 서평가이자 독서 마케팅 및 SEO/AEO 전문가입니다.
아래는 도서 '{book_title}'를 {total_parts}개 파트로 나누어 분석한 부분 요약들입니다.
이 요약들을 종합하여 하나의 완성된 블로그 서평 마크다운 포스팅을 작성해 주세요.
{series_notice}

--- 부분 요약 시작 ---
{partial_summaries}
--- 부분 요약 끝 ---

아래의 출력 형식을 정확히 준수하여 작성해 주세요.
""" + SUMMARY_PROMPT_TEMPLATE.replace("{series_notice}", "").replace("{book_content_section}", "")


class PDFSummarizer:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.7-flash"):
        """
        Gemini API를 이용한 PDF 요약기 초기화

        :param api_key: Gemini API 키 (None이면 환경변수 GEMINI_API_KEY 사용)
        :param model_name: 사용할 모델명 (기본: gemini-3.7-flash)
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY가 설정되지 않았습니다. .env 파일에 GEMINI_API_KEY를 입력하거나 생성자에 전달하세요."
            )
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def _generate_content_with_retry(
        self,
        contents: list,
        max_retries: int = 5,
        default_wait: float = 35.0
    ):
        """
        API 호출 중 발생하는 에러(503, 500, 429, 404 등)를 구분하여 자동 재시도 및 모델 폴백을 수행합니다.
        - 503 UNAVAILABLE / High Demand / 서버 일시적 과부하 → 점진적 대기 후 재시도 (최대 재시도 초과 시 대체 모델로 전환)
        - 429 일일 할당량(PerDay/FreeTier) 초과 → 대체 모델로 즉시 전환
        - 429 분당 토큰/요청 한도(RPM/TPM) 초과 → 대기 후 재시도
        - 404 NOT_FOUND / 모델 미지원 → 대체 모델로 즉시 전환
        """
        import re
        gen_config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )

        # 현재 모델 + 대체 모델 순서대로 시도할 목록 구성
        models_to_try = [self.model_name] + [m for m in FALLBACK_MODELS if m != self.model_name]

        for model in models_to_try:
            for attempt in range(1, max_retries + 1):
                try:
                    return self.client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=gen_config
                    )
                except Exception as e:
                    err_str = str(e)
                    is_quota_error = any(keyword in err_str for keyword in ["429", "RESOURCE_EXHAUSTED", "Quota exceeded"])
                    is_server_error = any(keyword in err_str for keyword in ["503", "500", "502", "504", "UNAVAILABLE", "high demand", "overloaded", "ServiceUnavailable", "InternalServerError"])
                    is_model_unavailable = any(keyword in err_str for keyword in ["404", "NOT_FOUND", "no longer available"])

                    if not is_quota_error and not is_server_error and not is_model_unavailable:
                        raise e

                    # 모델 폐지/미지원 (404) → 즉시 다음 대체 모델로
                    if is_model_unavailable:
                        print(f"\n   [!] ⛔ '{model}' 모델은 더 이상 사용할 수 없습니다.")
                        break

                    # 서버 일시적 과부하 (503 High Demand / UNAVAILABLE / 500 등) → 대기 후 재시도
                    if is_server_error:
                        if attempt < max_retries:
                            wait_seconds = 15.0 * attempt
                            print(f"\n   [*] ⏳ '{model}' Google 서버 일시 과부하(503 High Demand) 감지...")
                            print(f"       {int(wait_seconds)}초 동안 대기 후 자동 재시도합니다... (시도 {attempt}/{max_retries})")
                            time.sleep(wait_seconds)
                            continue
                        else:
                            print(f"\n   [!] ⛔ '{model}' 모델 서버 과부하 지속으로 최대 재시도 횟수 초과.")
                            break  # 다음 대체 모델로 전환

                    # 일일 할당량 초과 (재시도 무의미) → 다음 대체 모델로 전환
                    is_daily_limit = any(keyword in err_str for keyword in [
                        "PerDay", "FreeTier", "free_tier"
                    ])

                    if is_daily_limit:
                        print(f"\n   [!] ⛔ '{model}' 모델의 일일 무료 할당량이 소진되었습니다.")
                        break  # 이 모델 재시도 중단, 다음 대체 모델로

                    # 분당 한도(RPM/TPM) 초과 → 대기 후 재시도
                    if attempt < max_retries:
                        wait_seconds = default_wait
                        match_delay = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                        if not match_delay:
                            match_delay = re.search(r"'retryDelay':\s*'(\d+)s'", err_str, re.IGNORECASE)

                        if match_delay:
                            wait_seconds = float(match_delay.group(1)) + 3.0
                        else:
                            wait_seconds = default_wait * attempt

                        print(f"\n   [*] ⏳ '{model}' 분당 토큰 할당량(RPM/TPM) 리셋 대기 중...")
                        print(f"       {int(wait_seconds)}초 동안 대기 후 자동 재시도합니다... (시도 {attempt}/{max_retries})")
                        time.sleep(wait_seconds)
                    else:
                        print(f"\n   [!] ⛔ '{model}' 모델 최대 재시도 횟수 초과.")
                        break  # 다음 대체 모델로
            else:
                # for-attempt 루프가 정상 완료 = 여기까지 오면 안 됨 (성공 시 return으로 탈출)
                continue

            # break로 빠져나온 경우: 다음 모델 시도 안내
            next_models = [m for m in models_to_try if models_to_try.index(m) > models_to_try.index(model)]
            if next_models:
                print(f"   [*] 🔄 대체 모델 '{next_models[0]}'(으)로 자동 전환하여 재시도합니다...")
                continue

        # 모든 모델 소진
        raise QuotaExhaustedError(
            f"모든 모델({', '.join(models_to_try)})의 호출이 실패(할당량 소진 또는 서버 오류)했습니다.\n"
            f"해결 방법:\n"
            f"  1. 잠시 후 다시 시도 (Google 서버 일시적 과부하인 경우)\n"
            f"  2. Google AI Studio에서 유료 결제 활성화 (https://aistudio.google.com/)\n"
            f"  3. .env 파일의 GEMINI_API_KEY를 다른 프로젝트의 키로 교체"
        )

    def summarize_series_to_markdown(
        self,
        pdf_paths: list[str | Path] | str | Path,
        book_title: str,
        cover_image_filename: str,
        output_md_path: str | Path,
        output_source_md_path: Optional[str | Path] = None,
        save_source: bool = False
    ) -> str:
        """
        단일 또는 다중(시리즈물) PDF 도서로부터 마크다운을 로컬 추출하여 Gemini API로 분석하고
        완성된 블로그용 서평 마크다운({도서명}_review.md)을 생성하며,
        save_source가 True인 경우 원문 마크다운({도서명}_source.md)을 함께 저장합니다.

        :param pdf_paths: 대상 PDF 파일 경로(들)
        :param book_title: 기본 도서명/시리즈명
        :param cover_image_filename: 마크다운에 삽입할 1권 커버 이미지 파일명
        :param output_md_path: 저장할 서평 마크다운 파일 경로
        :param output_source_md_path: 저장할 원문 마크다운 파일 경로 (None이면 output_md_path 디렉토리에 자동 설정)
        :param save_source: 원문 마크다운 파일 저장 여부 (기본값: False)
        :return: 생성된 서평 마크다운 파일 절대 경로
        """
        if isinstance(pdf_paths, (str, Path)):
            pdf_paths = [pdf_paths]
        
        paths = [Path(p) for p in pdf_paths]
        output_md_path = Path(output_md_path)
        if output_source_md_path is None:
            output_source_md_path = output_md_path.parent / f"{book_title}_source.md"
        else:
            output_source_md_path = Path(output_source_md_path)

        is_series = len(paths) > 1

        if is_series:
            series_notice = (
                f"## 📚 시리즈물 특별 지침\n"
                f"- 본 도서는 총 {len(paths)}권으로 구성된 완결/연재 시리즈물입니다.\n"
                f"- 각 권별로 단편적 요약을 나열하지 마시고, 1권부터 전체 권수를 아우르는 중심 스토리와 세계관의 발전, "
                f"인물 간의 긴밀한 관계 변화, 시리즈 전체의 매력 포인트를 관통하는 하나의 완성도 높은 종합 서평으로 작성해 주세요."
            )
            display_title = f"{book_title} (전 {len(paths)}권 시리즈)"
        else:
            series_notice = ""
            display_title = book_title

        # 1. 로컬에서 도서 원문 마크다운 텍스트 준비 (기존 _source.md 캐시 우선 확인)
        has_cached_source = output_source_md_path.exists() and output_source_md_path.stat().st_size > 0
        if has_cached_source:
            with open(output_source_md_path, "r", encoding="utf-8") as f:
                full_book_content = f.read().strip()
            print(f"     - [⚡ 캐시 활용] 기존 도서 원문 마크다운 로드 완료: {output_source_md_path.name} ({len(full_book_content):,}자)")
        else:
            extracted_texts = []
            for idx, p in enumerate(paths, 1):
                label = f"[{idx}/{len(paths)}권] " if is_series else ""
                print(f"     - {label}'{p.name}' 로컬 마크다운 텍스트 추출 중...")
                txt = extract_markdown_from_pdf(p)
                if is_series:
                    extracted_texts.append(f"## 📖 제 {idx}권 ({p.stem})\n\n{txt}")
                else:
                    extracted_texts.append(txt)

            full_book_content = "\n\n---\n\n".join(extracted_texts).strip()

        # 2. 텍스트 레이어 존재 여부 판별 (OCR 완료 vs 순수 스캔본)
        has_text_layer = len(full_book_content) >= 50

        if has_text_layer:
            # === [도서 원문 마크다운 파일 저장 (--source 옵션 시, 미존재 시에만 신규 저장)] ===
            if save_source and not has_cached_source:
                output_source_md_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_source_md_path, "w", encoding="utf-8") as f:
                    f.write(full_book_content)
                print(f"     - [✓] 도서 원문 마크다운 저장 완료: {output_source_md_path.name} ({len(full_book_content):,}자)")

            # [장편 시리즈 최적화: 3권 이상이거나 총 텍스트가 30만 자를 초과하는 시리즈]
            is_large_series = is_series and (len(paths) >= 3 or len(full_book_content) > 300_000)

            if is_large_series:
                print(f"     - [📚 장편 시리즈 최적화] 총 {len(paths)}권 권별 핵심 요약 후 최종 통합 파이프라인 가동...")
                partial_summaries = []
                for idx, p in enumerate(paths, 1):
                    label = f"[{idx}/{len(paths)}권] '{p.name}'"
                    print(f"     - {label} 권별 핵심 요약 생성 중...")
                    vol_text = extract_markdown_from_pdf(p)
                    if not vol_text.strip():
                        vol_text = f"(제 {idx}권 내용 추출)"
                    part_prompt = PARTIAL_TEXT_SUMMARY_PROMPT.format(
                        book_title=f"{book_title} 제{idx}권 ({p.stem})",
                        part_num=idx,
                        total_parts=len(paths),
                        chunk_text=vol_text
                    )
                    response = self._generate_content_with_retry(contents=[part_prompt])
                    partial_summaries.append(f"### 제{idx}권 ({p.stem}) 핵심 요약\n{response.text or ''}")
                    print(f"       [✓] {label} 요약 완료")
                    if idx < len(paths):
                        print(f"       [*] ⏳ 권별 호출 간 안전 쿨다운 대기 중 (15초)...")
                        time.sleep(15.0)

                print(f"       [*] ⏳ 최종 시리즈 종합 서평 생성 전 대기 중 (15초)...")
                time.sleep(15.0)
                print(f"     - 전 {len(paths)}권 권별 요약들을 종합하여 최종 통합 서평 생성 중...")
                merged_summaries = "\n\n".join(partial_summaries)
                merge_prompt = MERGE_SUMMARY_PROMPT.format(
                    book_title=display_title,
                    total_parts=len(paths),
                    series_notice=series_notice,
                    partial_summaries=merged_summaries,
                    cover_image_filename=cover_image_filename
                )
                response = self._generate_content_with_retry(contents=[merge_prompt])
                markdown_content = response.text or ""
            else:
                # === [일반 도서 및 소형 시리즈: 고속 1회 텍스트 프롬프트 모드] ===
                print(f"     - AI 서평 및 SEO/AEO 마크다운 생성 요청 중 (고속 텍스트 모드)...")

                book_content_section = f"\n--- 📖 도서 본문 내용 시작 ---\n{full_book_content}\n--- 📖 도서 본문 내용 끝 ---\n"
                prompt = SUMMARY_PROMPT_TEMPLATE.format(
                    book_title=display_title,
                    cover_image_filename=cover_image_filename,
                    series_notice=series_notice,
                    book_content_section=book_content_section
                )

                try:
                    response = self._generate_content_with_retry(contents=[prompt])
                    markdown_content = response.text or ""
                except Exception as e:
                    err_str = str(e)
                    is_token_exceeded = "INVALID_ARGUMENT" in err_str and "token" in err_str.lower()
                    if not is_token_exceeded:
                        raise e

                    # 토큰 초과 시 텍스트 분할 요약 모드로 전환
                    print(f"\n   [*] 📄 입력 토큰 한도 초과! 텍스트 분할 요약 모드로 자동 전환합니다...")
                    markdown_content = self._summarize_chunked_text(
                        full_text=full_book_content,
                        book_title=display_title,
                        cover_image_filename=cover_image_filename,
                        series_notice=series_notice
                    )
        else:
            # === [스캔 이미지 PDF 폴백 모드 (Files API 멀티모달)] ===
            print(f"     - [!] 텍스트 레이어가 없는 스캔 이미지 PDF 감지 -> Gemini 멀티모달 파일 업로드 모드로 자동 전환...")
            markdown_content = self._summarize_multimodal_pdf(
                pdf_paths=paths,
                book_title=display_title,
                cover_image_filename=cover_image_filename,
                series_notice=series_notice
            )

        # 3. 마크다운 후처리 및 파일 저장
        markdown_content = postprocess_markdown(markdown_content)
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return str(output_md_path.resolve())

    def _summarize_chunked_text(
        self,
        full_text: str,
        book_title: str,
        cover_image_filename: str,
        series_notice: str,
        num_chunks: int = 3
    ) -> str:
        """
        토큰 한도를 초과하는 대용량 도서 텍스트를 N개 구간으로 분할하여 부분 요약 후 통합합니다.
        """
        chunk_len = len(full_text) // num_chunks
        chunks = []
        for i in range(num_chunks):
            start = i * chunk_len
            end = (i + 1) * chunk_len if i < num_chunks - 1 else len(full_text)
            chunks.append(full_text[start:end])

        print(f"     - 총 {num_chunks}개 파트로 텍스트 분할 완료. 파트별 요약을 시작합니다...")
        partial_summaries = []
        for idx, chunk in enumerate(chunks, 1):
            print(f"     - [{idx}/{num_chunks}] 텍스트 파트 요약 중...")
            part_prompt = PARTIAL_TEXT_SUMMARY_PROMPT.format(
                book_title=book_title,
                part_num=idx,
                total_parts=num_chunks,
                chunk_text=chunk
            )
            response = self._generate_content_with_retry(contents=[part_prompt])
            partial_summaries.append(f"### 파트 {idx}/{num_chunks}\n{response.text or ''}")
            print(f"       [✓] 파트 {idx} 요약 완료")
            if idx < num_chunks:
                print(f"       [*] ⏳ 분할 파트 간 토큰 한도(TPM) 보호 대기 중 (15초)...")
                time.sleep(15.0)

        print(f"       [*] ⏳ 최종 통합 서평 생성 전 대기 중 (15초)...")
        time.sleep(15.0)
        print(f"     - 부분 요약 {len(partial_summaries)}개를 통합하여 최종 서평 생성 중...")
        merged_summaries = "\n\n".join(partial_summaries)
        merge_prompt = MERGE_SUMMARY_PROMPT.format(
            book_title=book_title,
            total_parts=num_chunks,
            series_notice=series_notice,
            partial_summaries=merged_summaries,
            cover_image_filename=cover_image_filename
        )
        response = self._generate_content_with_retry(contents=[merge_prompt])
        return postprocess_markdown(response.text or "")

    def _summarize_multimodal_pdf(
        self,
        pdf_paths: list[Path],
        book_title: str,
        cover_image_filename: str,
        series_notice: str
    ) -> str:
        """
        텍스트 레이어가 없는 스캔 PDF를 Gemini Files API로 업로드하여 멀티모달로 요약합니다.
        """
        is_series = len(pdf_paths) > 1
        uploaded_files = []
        try:
            for idx, p in enumerate(pdf_paths, 1):
                label = f"[{idx}/{len(pdf_paths)}권] " if is_series else ""
                print(f"     - {label}'{p.name}' Gemini 서버로 업로드 중...")
                with open(p, "rb") as f:
                    uf = self.client.files.upload(
                        file=f,
                        config=dict(
                            mime_type="application/pdf",
                            display_name=p.name
                        )
                    )
                uploaded_files.append(uf)

            for idx, uf in enumerate(uploaded_files, 1):
                while uf.state.name == "PROCESSING":
                    label = f"[{idx}/{len(uploaded_files)}권] " if is_series else ""
                    print(f"     - {label}'{uf.display_name}' Gemini 문서 인덱싱 대기 중...")
                    time.sleep(3)
                    uf = self.client.files.get(name=uf.name)

                if uf.state.name == "FAILED":
                    raise RuntimeError(f"Gemini 파일 처리 실패: {uf.display_name}")

            prompt = SUMMARY_PROMPT_TEMPLATE.format(
                book_title=book_title,
                cover_image_filename=cover_image_filename,
                series_notice=series_notice,
                book_content_section=""
            )

            print(f"     - AI 서평 및 SEO/AEO 마크다운 생성 요청 중 (멀티모달 비전 모드)...")
            try:
                response = self._generate_content_with_retry(
                    contents=[*uploaded_files, prompt]
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e)
                is_token_exceeded = "INVALID_ARGUMENT" in err_str and "token" in err_str.lower()
                if not is_token_exceeded:
                    raise e

                print(f"\n   [*] 📄 입력 토큰 한도 초과! PDF 분할 요약 모드로 자동 전환합니다...")
                return self._summarize_chunked_pdf(
                    pdf_paths=pdf_paths,
                    book_title=book_title,
                    cover_image_filename=cover_image_filename,
                    series_notice=series_notice
                )
        finally:
            for uf in uploaded_files:
                try:
                    self.client.files.delete(name=uf.name)
                except Exception:
                    pass

    def _summarize_chunked_pdf(
        self,
        pdf_paths: list[Path],
        book_title: str,
        cover_image_filename: str,
        series_notice: str,
        num_parts: int = 3
    ) -> str:
        """
        토큰 한도를 초과하는 대용량 스캔 PDF를 분할하여 부분 요약 후 통합합니다.
        """
        all_split_files = []
        partial_summaries = []

        try:
            for pdf_path in pdf_paths:
                parts = split_pdf_into_parts(pdf_path, num_parts=num_parts)
                all_split_files.extend(parts)

            total_parts = len(all_split_files)
            print(f"     - 총 {total_parts}개 파트로 분할 완료. 파트별 요약을 시작합니다...")

            for idx, part_path in enumerate(all_split_files, 1):
                print(f"     - [{idx}/{total_parts}] 파트 업로드 및 요약 중...")
                uploaded = None
                try:
                    with open(part_path, "rb") as f:
                        uploaded = self.client.files.upload(
                            file=f,
                            config=dict(
                                mime_type="application/pdf",
                                display_name=part_path.name
                            )
                        )

                    while uploaded.state.name == "PROCESSING":
                        time.sleep(3)
                        uploaded = self.client.files.get(name=uploaded.name)

                    part_prompt = PARTIAL_PDF_SUMMARY_PROMPT.format(
                        part_num=idx, total_parts=total_parts
                    )
                    response = self._generate_content_with_retry(
                        contents=[uploaded, part_prompt]
                    )
                    partial_summaries.append(
                        f"### 파트 {idx}/{total_parts}\n{response.text or ''}"
                    )
                    print(f"       [✓] 파트 {idx} 요약 완료")
                    if idx < total_parts:
                        print(f"       [*] ⏳ 분할 파트 간 토큰 한도(TPM) 보호 대기 중 (15초)...")
                        time.sleep(15.0)

                finally:
                    if uploaded:
                        try:
                            self.client.files.delete(name=uploaded.name)
                        except Exception:
                            pass

            print(f"       [*] ⏳ 최종 통합 서평 생성 전 대기 중 (15초)...")
            time.sleep(15.0)
            print(f"     - 부분 요약 {len(partial_summaries)}개를 통합하여 최종 서평 생성 중...")
            merged_summaries = "\n\n".join(partial_summaries)
            merge_prompt = MERGE_SUMMARY_PROMPT.format(
                book_title=book_title,
                total_parts=total_parts,
                series_notice=series_notice,
                partial_summaries=merged_summaries,
                cover_image_filename=cover_image_filename
            )

            response = self._generate_content_with_retry(contents=[merge_prompt])
            return response.text or ""

        finally:
            original_paths = {p.resolve() for p in pdf_paths}
            for f in all_split_files:
                try:
                    if f.resolve() not in original_paths and f.exists():
                        os.unlink(f)
                except Exception:
                    pass

    def summarize_pdf_to_markdown(
        self,
        pdf_path: str | Path,
        cover_image_filename: str,
        output_md_path: str | Path,
        output_source_md_path: Optional[str | Path] = None,
        save_source: bool = False
    ) -> str:
        """
        단일 PDF 요약용 편의 메서드 (기존 인터페이스 호환)
        """
        pdf_path = Path(pdf_path)
        return self.summarize_series_to_markdown(
            pdf_paths=[pdf_path],
            book_title=pdf_path.stem,
            cover_image_filename=cover_image_filename,
            output_md_path=output_md_path,
            output_source_md_path=output_source_md_path,
            save_source=save_source
        )

