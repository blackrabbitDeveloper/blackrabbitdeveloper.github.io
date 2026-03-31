#!/usr/bin/env python3
"""
BlackRabbit LAB — 포스트 썸네일 자동 생성기
Pillow로 카테고리별 브랜드 썸네일(600x300)을 생성하고 front matter에 image 삽입.

사용법:
    python _tools/generate_thumbnails.py              # 전체 일괄 생성
    python _tools/generate_thumbnails.py --post FILE  # 단일 포스트
    python _tools/generate_thumbnails.py --force      # 전체 강제 재생성
"""

import argparse
import os
import re
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
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

# ── 카테고리별 그라디언트 색상 ──
CATEGORY_COLORS = {
    "기업 분석": (12, 74, 110),    # sky-900
    "경제 공부": (76, 29, 149),    # violet-900
    "투자 기초": (30, 58, 95),     # blue-900
    "시장분석":  (6, 78, 59),      # emerald-900
    "재테크":    (6, 95, 70),      # emerald-800
    "etf·펀드":  (120, 53, 15),    # amber-900
    "뉴스 해설": (131, 24, 67),    # pink-900
}
DEFAULT_COLOR = (39, 39, 42)  # zinc-800


def get_category_color(category):
    """카테고리명(lowercase)으로 그라디언트 시작 색상 반환."""
    cat = category.strip().lower() if category else ""
    for key, color in CATEGORY_COLORS.items():
        if key.lower() == cat:
            return color
    return DEFAULT_COLOR


def lerp_color(c1, c2, t):
    """두 색상 사이를 선형 보간."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def generate_thumbnail(category, output_path):
    """카테고리별 브랜드 썸네일 생성."""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # 대각선 그라디언트 (좌상 → 우하)
    top_color = get_category_color(category)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            t = (x / WIDTH + y / HEIGHT) / 2.0
            color = lerp_color(top_color, BG_BASE, t)
            img.putpixel((x, y), color)

    # 폰트 로드
    try:
        font_title = ImageFont.truetype(FONT_BOLD, 24)
        font_cat = ImageFont.truetype(FONT_MEDIUM, 16)
    except OSError:
        print(f"  경고: 폰트 파일을 찾을 수 없습니다. 기본 폰트 사용.")
        font_title = ImageFont.load_default()
        font_cat = ImageFont.load_default()

    # "BlackRabbit Lab" 텍스트
    title_text = "BlackRabbit Lab"
    title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = (WIDTH - title_w) // 2
    title_y = HEIGHT // 2 - 40
    draw.text((title_x, title_y), title_text, fill=(255, 255, 255), font=font_title)

    # 구분선
    line_w = 60
    line_x = (WIDTH - line_w) // 2
    line_y = HEIGHT // 2 - 2
    draw.rectangle([line_x, line_y, line_x + line_w, line_y + 2], fill=BRAND_COLOR)

    # 카테고리명
    cat_display = category if category else "기타"
    cat_bbox = draw.textbbox((0, 0), cat_display, font=font_cat)
    cat_w = cat_bbox[2] - cat_bbox[0]
    cat_x = (WIDTH - cat_w) // 2
    cat_y = HEIGHT // 2 + 14
    draw.text((cat_x, cat_y), cat_display, fill=BRAND_COLOR, font=font_cat)

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
            # 배열 처리: [a, b, c]
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

    # 이미 image 필드가 있으면 스킵
    if re.search(r"^image:", content, re.MULTILINE):
        return False

    # description: 뒤에 삽입, 없으면 첫 번째 --- 뒤에 삽입
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

    # 이미지가 이미 있고 force가 아니면 스킵
    if os.path.exists(png_path) and not force:
        print(f"  스킵: {md_filename} (이미지 존재)")
        return "skipped"

    fm = parse_front_matter(md_path)
    category = get_first_category(fm)

    try:
        generate_thumbnail(category, png_path)
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
