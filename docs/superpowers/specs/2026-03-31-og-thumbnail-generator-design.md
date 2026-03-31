# 포스트 썸네일 이미지 자동 생성 — 디자인 스펙

## 개요

Python Pillow로 포스트별 브랜드 썸네일 이미지(600x300 PNG)를 자동 생성하여 사이트 내 카드 썸네일로 사용한다. 기존 SVG placeholder의 상위 호환.

## 결정사항

- **용도**: 사이트 썸네일 전용 (OG는 기존 `main.png` 유지)
- **실행 방식**: 독립 일괄 실행 + post_maker.py 통합
- **디자인**: 브랜드 강조 (BlackRabbit Lab 워드마크 + 카테고리명)
- **크기**: 600x300 PNG
- **front matter**: 자동 `image:` 삽입/수정
- **구현**: Pillow 단독

## 이미지 디자인

```
┌──────────────────────────────────────────┐
│  (카테고리별 그라디언트 배경)               │
│                                          │
│         BlackRabbit Lab                  │
│         ─── (brand 컬러 라인) ───          │
│         카테고리명                         │
│                                          │
└──────────────────────────────────────────┘
```

- **배경**: 카테고리별 그라디언트 (좌상→우하 대각선)
- **중앙 상단**: "BlackRabbit Lab" — Noto Sans KR Bold, 흰색, 24px
- **구분선**: `#3ECF8E` 가로선, 60px 너비, 2px 두께
- **중앙 하단**: 카테고리명 — Noto Sans KR Medium, `#3ECF8E`, 16px
- **포맷**: PNG, 예상 ~10-30KB

### 카테고리별 그라디언트 매핑

| 카테고리 | 좌상 색상 | 우하 색상 |
|---------|----------|----------|
| 기업 분석 | `#0c4a6e` (sky-900) | `#0a0a0a` |
| 경제 공부 | `#4c1d95` (violet-900) | `#0a0a0a` |
| 투자 기초 | `#1e3a5f` (blue-900) | `#0a0a0a` |
| 시장분석 | `#064e3b` (emerald-900) | `#0a0a0a` |
| 재테크 | `#065f46` (emerald-800) | `#0a0a0a` |
| ETF·펀드 | `#78350f` (amber-900) | `#0a0a0a` |
| 뉴스 해설 | `#831843` (pink-900) | `#0a0a0a` |
| 기타 | `#27272a` (zinc-800) | `#0a0a0a` |

## 파일 구조

### 새 파일: `_tools/generate_thumbnails.py`

**CLI 사용법:**
```bash
# 전체 포스트 일괄 생성 (이미 있으면 스킵)
python _tools/generate_thumbnails.py

# 단일 포스트만 생성
python _tools/generate_thumbnails.py --post 2026-03-09-apple-analysis-and-future-outlook.md

# 전체 강제 재생성
python _tools/generate_thumbnails.py --force
```

**핵심 함수:**
- `generate_thumbnail(category: str, output_path: str)` — 이미지 생성
- `parse_front_matter(md_path: str) -> dict` — front matter 파싱
- `inject_image_field(md_path: str, image_path: str)` — front matter에 `image:` 삽입
- `process_all_posts(force: bool)` — 일괄 처리
- `process_single_post(filename: str)` — 단일 처리

### 출력 경로

`assets/img/posts/{포스트파일명 without .md}.png`

예: `2026-03-09-apple-analysis-and-future-outlook.md`
→ `assets/img/posts/2026-03-09-apple-analysis-and-future-outlook.png`

### 폰트 파일

`_tools/fonts/NotoSansKR-Bold.ttf`, `_tools/fonts/NotoSansKR-Medium.ttf`

Google Fonts에서 다운로드하여 저장. `.gitignore`에 포함하지 않음 (빌드에 필요).

### post_maker.py 통합

포스트 생성 완료 후:
```python
from generate_thumbnails import generate_thumbnail, inject_image_field
```
로 호출하여 썸네일 자동 생성 + front matter 삽입.

## 일괄 생성 로직

1. `_posts/` 폴더의 모든 `.md` 파일 스캔
2. 각 파일의 front matter에서 `categories` 첫 번째 값 추출
3. `assets/img/posts/`에 해당 PNG가 이미 있으면 스킵 (`--force` 시 덮어쓰기)
4. Pillow로 이미지 생성 → `assets/img/posts/`에 저장
5. front matter에 `image:` 필드가 없으면 자동 삽입, 있으면 스킵
6. 결과 요약: `생성: N개, 스킵: M개`

## front matter 수정 규칙

- `image:` 필드가 없는 경우: `description:` 아래에 `image: /assets/img/posts/{filename}.png` 삽입
- `image:` 필드가 이미 있는 경우: 수정하지 않음 (사용자가 직접 설정한 이미지 존중)
- YAML 파싱은 정규식으로 처리 (PyYAML 의존성 회피)

## 의존성

- `Pillow` (`pip install Pillow`)
- Noto Sans KR TTF 파일 (Bold, Medium) → `_tools/fonts/`
- Python 표준 라이브러리: `os`, `re`, `argparse`, `pathlib`

## 기존 SVG placeholder와의 관계

- 이미지가 생성되어 `image:` front matter가 추가되면, 사이트에서는 `<img>` 태그로 표시됨
- SVG placeholder (`_includes/category-icon.html`)는 `image`가 없는 포스트의 fallback으로 유지
- 점진적 전환: 기존 포스트에 일괄 적용 후, 신규 포스트는 post_maker.py가 자동 처리
