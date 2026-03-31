# Thumbnail Placeholder 개선 — 디자인 스펙

## 개요

포스트에 `image` front matter가 없을 때 표시되는 빈 그라디언트 placeholder를 카테고리별 SVG 아이콘 + 텍스트로 개선한다.

## 현황

- 25개 포스트 모두 `image` 없음
- 3곳에서 placeholder 사용: featured card (`home.html:18`), grid card (`home.html:148`), post detail cover (`post.html:53`)
- 현재: 카테고리별 그라디언트 배경만 표시, `card-thumb-placeholder`에 `opacity: 0.15`

## 결정사항

- **스타일**: 미니멀 라인 아이콘 + 카테고리명 텍스트 (Style A)
- **Opacity**: 중간 밸런스 — 아이콘 stroke 0.6, 텍스트 0.5 (Option C)
- **구현 방식**: Jekyll Include (`_includes/category-icon.html`)

## 카테고리별 아이콘 & 컬러 매핑

| 카테고리 | 아이콘 | 컬러 | 그라디언트 |
|---------|--------|------|-----------|
| 기업 분석 | 빌딩 | sky-400 `rgba(56,189,248)` | from-sky-400 to-sky-600 |
| 경제 공부 | 책 | violet-400 `rgba(167,139,250)` | from-violet-400 to-violet-600 |
| 투자 기초 | 바 차트 | blue-400 `rgba(96,165,250)` | from-blue-400 to-blue-600 |
| 시장분석 | 파형 | emerald-500 `rgba(52,211,153)` | from-emerald-500 to-emerald-700 |
| 재테크 | 동전 | emerald-300 `rgba(110,231,183)` | from-emerald-300 to-emerald-500 |
| ETF·펀드 | 파이 차트 | amber-400 `rgba(251,191,36)` | from-amber-400 to-amber-600 |
| 뉴스 해설 | 신문 | pink-400 `rgba(244,114,182)` | from-pink-400 to-pink-500 |
| 기타 | 격자 | zinc-400 `rgba(161,161,170)` | from-zinc-400 to-zinc-600 |

## 구현 구조

### 새 파일: `_includes/category-icon.html`

- 파라미터: `cat` (카테고리 downcased), `size` (sm/md/lg)
- size별 아이콘 크기: sm=24px, md=32px (기본), lg=48px
- 카테고리별 if/elsif 로 SVG + 텍스트 출력
- 텍스트: `font-family: JetBrains Mono`, `text-transform: uppercase`, `letter-spacing: 0.1em`

### 수정 파일

| 파일 | 위치 | 변경 내용 | size |
|------|------|----------|------|
| `_layouts/home.html` | featured card (~line 18) | `{% else %}` 블록에 include 추가 | lg |
| `_layouts/home.html` | grid card (~line 148) | `{% else %}` 블록에 include 추가 | md |
| `_layouts/post.html` | post detail cover (~line 53) | `{% else %}` 블록에 include 추가 | lg |
| `css/styles.css` | `.card-thumb-placeholder` | opacity 규칙 수정, 라이트 모드 조정 |

### placeholder div 변경

기존:
```html
<div class="card-thumb-placeholder bg-gradient-to-br from-sky-400 to-sky-600"></div>
```

변경 후:
```html
<div class="card-thumb-placeholder bg-gradient-to-br from-sky-400/15 to-sky-600/5">
  {% include category-icon.html cat=post_cat size="md" %}
</div>
```

그라디언트 opacity를 3곳 모두 `/15`, `/5`로 통일 (featured card, post detail에서 이미 사용 중인 값). Grid card는 기존 opacity 없는 클래스(`from-sky-400 to-sky-600`) + CSS `opacity: 0.15` 조합에서 Tailwind `/15`, `/5` 방식으로 전환.

### CSS 변경

- `.card-thumb-placeholder`에서 `opacity: 0.15` 제거 → include 내부에서 아이콘/텍스트 opacity 직접 제어
- `display: flex; align-items: center; justify-content: center;` 유지
- 라이트 모드: `[data-theme="light"] .card-thumb-placeholder { opacity: 0.1; }` 제거

### 라이트 모드

- 아이콘 stroke opacity: 0.6 → 라이트 모드에서도 동일 (배경이 밝아서 자연스럽게 더 잘 보임)
- 별도 CSS 추가 불필요

## 정리 작업

- `_mockup/` 폴더 삭제
- `.gitignore`에 `_mockup/` 추가

## 향후 (옵션 3)

Python 스크립트로 포스트별 OG 이미지 자동 생성 → `assets/img/posts/` 에 저장 → `image` front matter 자동 추가. 이 스펙의 범위 밖.
