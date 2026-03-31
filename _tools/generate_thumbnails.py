#!/usr/bin/env python3
"""
BlackRabbit LAB — 포스트 썸네일 자동 생성기 v3
카테고리별 배경 이미지 + 어두운 오버레이 + brand 요소로 썸네일 생성.

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
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
except ImportError:
    print("Pillow가 필요합니다: pip install Pillow")
    sys.exit(1)

# ── 경로 설정 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
POSTS_DIR = os.path.join(PROJECT_ROOT, "_posts")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "assets", "img", "posts")
FONT_DIR = os.path.join(SCRIPT_DIR, "fonts")
BG_DIR = os.path.join(SCRIPT_DIR, "backgrounds")

FONT_BOLD = os.path.join(FONT_DIR, "NotoSansKR-Bold.ttf")
FONT_MEDIUM = os.path.join(FONT_DIR, "NotoSansKR-Medium.ttf")

# ── 이미지 설정 ──
WIDTH = 600
HEIGHT = 300
BRAND_COLOR = (62, 207, 142)  # #3ECF8E

# ── 카테고리별 배경 이미지 + accent 색상 ──
CATEGORY_MAP = {
    "기업 분석": ("company.jpg",  (56, 189, 248)),   # sky
    "경제 공부": ("economics.jpg", (167, 139, 250)),  # violet
    "투자 기초": ("investment.jpg", (96, 165, 250)),  # blue
    "시장분석":  ("market.jpg",   (52, 211, 153)),    # emerald
    "재테크":    ("finance.jpg",  (110, 231, 183)),   # emerald-light
    "etf·펀드":  ("etf.jpg",      (251, 191, 36)),    # amber
    "뉴스 해설": ("news.jpg",     (244, 114, 182)),   # pink
}
DEFAULT_MAP = ("default.jpg", (161, 161, 170))  # zinc


def get_category_config(category):
    """카테고리명으로 (배경파일, accent색상) 반환."""
    cat = category.strip().lower() if category else ""
    for key, config in CATEGORY_MAP.items():
        if key.lower() == cat:
            return config
    return DEFAULT_MAP


def load_background(bg_filename):
    """배경 이미지를 로드하고 600x300으로 리사이즈/크롭."""
    bg_path = os.path.join(BG_DIR, bg_filename)
    if not os.path.exists(bg_path):
        # fallback: 단색 배경
        return Image.new("RGB", (WIDTH, HEIGHT), (15, 15, 15))

    img = Image.open(bg_path).convert("RGB")

    # 비율 맞춰서 크롭
    target_ratio = WIDTH / HEIGHT
    img_ratio = img.width / img.height

    if img_ratio > target_ratio:
        # 이미지가 더 넓음 → 좌우 크롭
        new_w = int(img.height * target_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    else:
        # 이미지가 더 높음 → 상하 크롭
        new_h = int(img.width / target_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))

    return img.resize((WIDTH, HEIGHT), Image.LANCZOS)


def apply_dark_overlay(img, opacity=0.55):
    """어두운 오버레이를 씌워서 텍스트 가독성 확보."""
    overlay = Image.new("RGB", (WIDTH, HEIGHT), (8, 8, 8))
    return Image.blend(img, overlay, opacity)


def apply_gradient_overlay(img, accent, strength=0.25):
    """카테고리 accent 색상으로 은은한 그라디언트 오버레이."""
    gradient = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = gradient.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            # 좌상단에서 우하단으로 accent → 투명
            t = (x / WIDTH * 0.5 + y / HEIGHT * 0.5)
            alpha = int((1.0 - t) * strength * 255)
            pixels[x, y] = (*accent, alpha)

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, gradient)
    return img.convert("RGB")


def draw_bottom_bar(draw):
    """하단에 brand 컬러 얇은 액센트 바."""
    draw.rectangle([0, HEIGHT - 3, WIDTH, HEIGHT], fill=BRAND_COLOR)


def draw_corner_accents(draw, accent):
    """좌상, 우하 코너에 미니멀 L자 라인."""
    draw.line([(16, 16), (16, 40)], fill=accent, width=1)
    draw.line([(16, 16), (40, 16)], fill=accent, width=1)
    draw.line([(WIDTH - 16, HEIGHT - 16), (WIDTH - 16, HEIGHT - 40)], fill=accent, width=1)
    draw.line([(WIDTH - 16, HEIGHT - 16), (WIDTH - 40, HEIGHT - 16)], fill=accent, width=1)


def generate_thumbnail(category, output_path, title=""):
    """카테고리별 브랜드 썸네일 생성 (v3: 배경 이미지 기반)."""
    bg_file, accent = get_category_config(category)

    # 1. 배경 이미지 로드 + 리사이즈
    img = load_background(bg_file)

    # 2. 약간 어둡게 + 채도 낮추기
    img = ImageEnhance.Color(img).enhance(0.7)
    img = apply_dark_overlay(img, opacity=0.52)

    # 3. accent 그라디언트 오버레이
    img = apply_gradient_overlay(img, accent, strength=0.18)

    draw = ImageDraw.Draw(img)

    # 4. 장식 요소
    draw_bottom_bar(draw)

    # 5. 폰트 로드
    try:
        font_cat = ImageFont.truetype(FONT_MEDIUM, 11)
        font_brand = ImageFont.truetype(FONT_MEDIUM, 10)
    except OSError:
        print("  경고: 폰트 파일을 찾을 수 없습니다.")
        font_cat = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    # 6. 브랜드명 (좌하단, brand 바 위)
    draw.text((16, HEIGHT - 22), "BlackRabbit Lab", fill=BRAND_COLOR, font=font_brand)

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
