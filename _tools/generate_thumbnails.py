#!/usr/bin/env python3
"""
BlackRabbit LAB — 포스트 썸네일 자동 생성기 v2
Pillow로 카테고리별 브랜드 썸네일(600x300)을 생성하고 front matter에 image 삽입.

사용법:
    python _tools/generate_thumbnails.py              # 전체 일괄 생성
    python _tools/generate_thumbnails.py --post FILE  # 단일 포스트
    python _tools/generate_thumbnails.py --force      # 전체 강제 재생성
"""

import argparse
import math
import os
import random
import re
import sys
import textwrap

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("Pillow가 필요합니다: pip install Pillow")
    sys.exit(1)

# ── 경로 설정 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
POSTS_DIR = os.path.join(PROJECT_ROOT, "_posts")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "assets", "img", "posts")
FONT_DIR = os.path.join(SCRIPT_DIR, "fonts")

FONT_BOLD = os.path.join(FONT_DIR, "NotoSansKR-Bold.ttf")
FONT_MEDIUM = os.path.join(FONT_DIR, "NotoSansKR-Medium.ttf")

# ── 이미지 설정 ──
WIDTH = 600
HEIGHT = 300
BRAND_COLOR = (62, 207, 142)  # #3ECF8E
BG_BASE = (10, 10, 10)  # #0a0a0a

# ── 카테고리별 그라디언트 색상 (밝은 accent + 어두운 base) ──
CATEGORY_COLORS = {
    "기업 분석": ((14, 116, 144), (12, 74, 110)),     # sky
    "경제 공부": ((124, 58, 237), (76, 29, 149)),      # violet
    "투자 기초": ((59, 130, 246), (30, 58, 95)),       # blue
    "시장분석":  ((16, 185, 129), (6, 78, 59)),        # emerald
    "재테크":    ((52, 211, 153), (6, 95, 70)),        # emerald-light
    "etf·펀드":  ((245, 158, 11), (120, 53, 15)),      # amber
    "뉴스 해설": ((236, 72, 153), (131, 24, 67)),      # pink
}
DEFAULT_COLOR = ((113, 113, 122), (39, 39, 42))  # zinc


def get_category_colors(category):
    """카테고리명으로 (accent, dark) 색상 쌍 반환."""
    cat = category.strip().lower() if category else ""
    for key, colors in CATEGORY_COLORS.items():
        if key.lower() == cat:
            return colors
    return DEFAULT_COLOR


def lerp_color(c1, c2, t):
    """두 색상 사이를 선형 보간."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_gradient(img, accent, dark):
    """대각선 그라디언트 배경 — 좌상 accent → 우하 dark."""
    pixels = img.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            t = (x / WIDTH * 0.6 + y / HEIGHT * 0.4)
            t = t ** 0.8  # 비선형 커브로 accent가 좀 더 넓게
            color = lerp_color(accent, dark, t)
            pixels[x, y] = color


def add_noise(img, intensity=12):
    """미세한 필름 그레인 텍스처 오버레이."""
    random.seed(42)  # 동일 결과 보장
    pixels = img.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r, g, b = pixels[x, y]
            noise = random.randint(-intensity, intensity)
            pixels[x, y] = (
                max(0, min(255, r + noise)),
                max(0, min(255, g + noise)),
                max(0, min(255, b + noise)),
            )


def add_vignette(img):
    """모서리 어둡게 — 비네트 효과."""
    pixels = img.load()
    cx, cy = WIDTH / 2, HEIGHT / 2
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            factor = 1.0 - (dist / max_dist) ** 2 * 0.35
            r, g, b = pixels[x, y]
            pixels[x, y] = (
                int(r * factor),
                int(g * factor),
                int(b * factor),
            )


def draw_corner_lines(draw, accent):
    """좌상, 우하 코너에 L자 라인 장식."""
    line_color = (*accent, 60)  # 반투명
    # 좌상단
    draw.line([(20, 20), (20, 50)], fill=accent, width=1)
    draw.line([(20, 20), (50, 20)], fill=accent, width=1)
    # 우하단
    draw.line([(WIDTH - 20, HEIGHT - 20), (WIDTH - 20, HEIGHT - 50)], fill=accent, width=1)
    draw.line([(WIDTH - 20, HEIGHT - 20), (WIDTH - 50, HEIGHT - 20)], fill=accent, width=1)


def draw_dot_pattern(draw, accent):
    """우상단 영역에 미세한 도트 패턴."""
    dot_color = (*accent[:3], 30) if len(accent) == 4 else accent
    # 낮은 opacity를 RGB로 시뮬레이션
    faded = tuple(c // 8 for c in accent[:3])
    for row in range(4):
        for col in range(6):
            x = WIDTH - 120 + col * 16
            y = 24 + row * 16
            draw.ellipse([x, y, x + 2, y + 2], fill=faded)


def draw_bottom_bar(draw):
    """하단에 brand 컬러 액센트 바."""
    draw.rectangle([0, HEIGHT - 3, WIDTH, HEIGHT], fill=BRAND_COLOR)


def wrap_title(title, font, max_width, draw):
    """제목을 max_width에 맞게 줄바꿈. 최대 2줄."""
    words = title.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = word
            if len(lines) >= 2:
                break
        else:
            current = test
    if current and len(lines) < 2:
        lines.append(current)
    # 2줄 초과 시 마지막 줄에 ... 추가
    if len(lines) == 2:
        remaining = " ".join(words[len(" ".join(lines).split()):])
        if remaining:
            lines[1] = lines[1]
            # 마지막 줄이 넘치면 잘라내기
            while True:
                test = lines[1] + "..."
                bbox = draw.textbbox((0, 0), test, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    lines[1] = test
                    break
                lines[1] = lines[1][:-1]
                if not lines[1]:
                    break
    return lines


def generate_thumbnail(category, output_path, title=""):
    """카테고리별 브랜드 썸네일 생성 (v2: 텍스처 + 장식 + 제목)."""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    accent, dark = get_category_colors(category)

    # 1. 그라디언트 배경
    draw_gradient(img, accent, dark)

    # 2. 비네트 효과
    add_vignette(img)

    # 3. 노이즈 텍스처
    add_noise(img, intensity=10)

    draw = ImageDraw.Draw(img)

    # 4. 장식 요소
    draw_corner_lines(draw, accent)
    draw_dot_pattern(draw, accent)
    draw_bottom_bar(draw)

    # 5. 폰트 로드
    try:
        font_title = ImageFont.truetype(FONT_BOLD, 22)
        font_cat = ImageFont.truetype(FONT_MEDIUM, 11)
        font_brand = ImageFont.truetype(FONT_MEDIUM, 10)
    except OSError:
        print("  경고: 폰트 파일을 찾을 수 없습니다. 기본 폰트 사용.")
        font_title = ImageFont.load_default()
        font_cat = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    # 6. 카테고리 뱃지 (좌상단)
    cat_display = category if category else "기타"
    cat_bbox = draw.textbbox((0, 0), cat_display, font=font_cat)
    cat_w = cat_bbox[2] - cat_bbox[0]
    cat_h = cat_bbox[3] - cat_bbox[1]
    badge_x, badge_y = 20, 60
    badge_pad_x, badge_pad_y = 10, 5
    # 뱃지 배경
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + cat_w + badge_pad_x * 2, badge_y + cat_h + badge_pad_y * 2],
        radius=4,
        fill=(*accent, 40),
        outline=accent,
    )
    draw.text((badge_x + badge_pad_x, badge_y + badge_pad_y), cat_display, fill=(255, 255, 255, 220), font=font_cat)

    # 7. 포스트 제목 (메인 텍스트, 좌측 정렬)
    if title:
        title_lines = wrap_title(title, font_title, WIDTH - 80, draw)
    else:
        title_lines = ["BlackRabbit Lab"]

    title_y = 110
    line_spacing = 34
    for i, line in enumerate(title_lines):
        # 텍스트 그림자
        draw.text((41, title_y + i * line_spacing + 1), line, fill=(0, 0, 0, 120), font=font_title)
        draw.text((40, title_y + i * line_spacing), line, fill=(255, 255, 255), font=font_title)

    # 8. 구분선 (제목 아래)
    sep_y = title_y + len(title_lines) * line_spacing + 8
    draw.rectangle([40, sep_y, 100, sep_y + 2], fill=BRAND_COLOR)

    # 9. 브랜드명 (좌하단)
    brand_text = "BlackRabbit Lab"
    draw.text((20, HEIGHT - 24), brand_text, fill=(*BRAND_COLOR, 180), font=font_brand)

    # 10. 날짜 영역 placeholder (우하단) — 선택적
    # draw.text((WIDTH - 120, HEIGHT - 24), "2026", fill=(255,255,255,60), font=font_brand)

    # 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", optimize=True)


def parse_front_matter(md_path):
    """마크다운 파일에서 front matter를 파싱하여 dict 반환."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}

    fm_text = match.group(1)
    result = {}
    for line in fm_text.split("\n"):
        m = re.match(r'^(\w[\w\s]*?):\s*(.+)$', line)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
            else:
                val = val.strip('"').strip("'")
            result[key] = val
    return result


def get_first_category(fm):
    """front matter에서 첫 번째 카테고리 추출."""
    cats = fm.get("categories", [])
    if isinstance(cats, list) and cats:
        return cats[0]
    if isinstance(cats, str):
        return cats
    return ""


def inject_image_field(md_path, image_path):
    """front matter에 image 필드가 없으면 삽입."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    if re.search(r"^image:", content, re.MULTILINE):
        return False

    image_line = f'image: {image_path}'
    if "description:" in content:
        content = re.sub(
            r'(description:\s*".+?")\s*\n',
            rf'\1\n{image_line}\n',
            content,
            count=1
        )
    else:
        content = content.replace("---\n", f"---\n{image_line}\n", 1)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def process_post(md_filename, force=False):
    """단일 포스트 처리. 반환: 'created', 'skipped', 'error'."""
    md_path = os.path.join(POSTS_DIR, md_filename)
    if not os.path.exists(md_path):
        print(f"  오류: {md_filename} 파일을 찾을 수 없습니다.")
        return "error"

    stem = os.path.splitext(md_filename)[0]
    png_path = os.path.join(OUTPUT_DIR, f"{stem}.png")
    web_path = f"/assets/img/posts/{stem}.png"

    if os.path.exists(png_path) and not force:
        print(f"  스킵: {md_filename} (이미지 존재)")
        return "skipped"

    fm = parse_front_matter(md_path)
    category = get_first_category(fm)
    title = fm.get("title", "")

    try:
        generate_thumbnail(category, png_path, title=title)
        injected = inject_image_field(md_path, web_path)
        status = "생성"
        if injected:
            status += " + front matter 수정"
        print(f"  {status}: {md_filename} → {stem}.png")
        return "created"
    except Exception as e:
        print(f"  오류: {md_filename} — {e}")
        return "error"


def process_all_posts(force=False):
    """전체 포스트 일괄 처리."""
    if not os.path.isdir(POSTS_DIR):
        print(f"오류: {POSTS_DIR} 디렉토리를 찾을 수 없습니다.")
        return

    md_files = sorted(f for f in os.listdir(POSTS_DIR) if f.endswith(".md"))
    if not md_files:
        print("포스트가 없습니다.")
        return

    print(f"총 {len(md_files)}개 포스트 처리 중...\n")
    created = skipped = errors = 0

    for md_file in md_files:
        result = process_post(md_file, force)
        if result == "created":
            created += 1
        elif result == "skipped":
            skipped += 1
        else:
            errors += 1

    print(f"\n완료: 생성 {created}개, 스킵 {skipped}개, 오류 {errors}개")


def main():
    parser = argparse.ArgumentParser(description="BlackRabbit LAB 포스트 썸네일 생성기")
    parser.add_argument("--post", help="단일 포스트 파일명 (예: 2026-03-09-apple-analysis.md)")
    parser.add_argument("--force", action="store_true", help="기존 이미지 덮어쓰기")
    args = parser.parse_args()

    if args.post:
        process_post(args.post, args.force)
    else:
        process_all_posts(args.force)


if __name__ == "__main__":
    main()
