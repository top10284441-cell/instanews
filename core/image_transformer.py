import os
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import BASE_DIR

FONT_DIR = BASE_DIR / "fonts"
FONT_BLACK = FONT_DIR / "Pretendard-Black.otf"
FONT_BOLD = FONT_DIR / "Pretendard-Bold.otf"
FONT_BACKUP_HEADLINE = FONT_DIR / "BlackHanSans-Regular.ttf"
SYS_KR_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
SYS_KR_REGULAR = r"C:\Windows\Fonts\malgun.ttf"

def get_headline_font(size: int = 54, weight: str = "Black") -> ImageFont.FreeTypeFont:
    """유튜브/인스타 영상과 동일한 볼드 고딕 헤드라인 폰트 (Bold / ExBold / Black 지원)"""
    font_file = FONT_BLACK
    if str(weight).lower() == "bold":
        font_file = FONT_BOLD
    elif str(weight).lower() in ("exbold", "extrabold"):
        font_file = FONT_BLACK
    else:
        font_file = FONT_BLACK

    if font_file.exists():
        return ImageFont.truetype(str(font_file), size)
    if FONT_BOLD.exists():
        return ImageFont.truetype(str(FONT_BOLD), size)
    if FONT_BACKUP_HEADLINE.exists():
        return ImageFont.truetype(str(FONT_BACKUP_HEADLINE), size)
    if os.path.exists(SYS_KR_BOLD):
        return ImageFont.truetype(SYS_KR_BOLD, size)
    return ImageFont.load_default()

def get_sub_font(size: int = 28, bold: bool = True) -> ImageFont.FreeTypeFont:
    """본문 및 로고용 깔끔한 서체"""
    target = FONT_BOLD if bold else FONT_BLACK
    if target.exists():
        return ImageFont.truetype(str(target), size)
    sys_font = SYS_KR_BOLD if bold else SYS_KR_REGULAR
    if os.path.exists(sys_font):
        return ImageFont.truetype(sys_font, size)
    return ImageFont.load_default()

def clean_pillow_text(text: str) -> str:
    """Pillow에서 네모([])로 깨지는 이모지 및 특수문자 안전 제거"""
    if not text:
        return ""
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]', flags=re.UNICODE)
    cleaned = emoji_pattern.sub("", text)
    cleaned = cleaned.replace("👉", ">").replace("▶", ">").replace("❤️", "").replace("🐾", "").replace("🔥", "").replace("⚡", "").strip()
    return cleaned

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
    """텍스트 자동 줄바꿈"""
    lines = []
    paragraphs = text.split("\n")
    for para in paragraphs:
        if not para.strip():
            continue
        words = para.split(" ")
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            if line_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    cur_part = ""
                    for char in word:
                        test_part = cur_part + char
                        b = draw.textbbox((0, 0), test_part, font=font)
                        if b[2] - b[0] <= max_width:
                            cur_part = test_part
                        else:
                            lines.append(cur_part)
                            cur_part = char
                    current_line = cur_part
        if current_line:
            lines.append(current_line)
    return lines

def create_cover_slide(
    source_image_path: Path,
    output_path: Path,
    title: str,
    logo_text: str = "",
    logo_path: str = None,
    logo_position: str = "center",
    font_size: int = 66,
    font_weight: str = "Black",
    offset_x: int = 0,
    offset_y: int = 0,
    grad_opacity: int = 85,
    grad_height: int = 50,
    target_aspect: str = "1:1"
) -> str:
    """
    [1번 슬라이드] 영상과 100% 동일한 바이럴 썸네일 표지 생성
    - 사진 전체가 캔버스 전체(1080x1080)를 꽉 채우는 풀 프레임
    - 하단 그라데이션 농도 및 높이 조절
    - 그라데이션 위에 2줄 순백색 굵은 고딕 헤드라인
    - 상단 중앙/좌/우에 은은한 로고 배치
    """
    w, h = (1080, 1080) if target_aspect == "1:1" else (1080, 1350)
    
    # 1. 원본 사진 로드 및 1:1 스마트 핏 (왜곡 없이 전체 채움)
    src = Image.open(source_image_path).convert("RGBA")
    src_w, src_h = src.size
    target_ratio = w / h
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        cropped = src.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        # 상단 인물/피사체 보존 위해 약간 상단 중심 크롭
        top = max(0, int((src_h - new_h) * 0.3))
        cropped = src.crop((0, top, src_w, top + new_h))

    photo = cropped.resize((w, h), Image.Resampling.LANCZOS)
    photo = photo.filter(ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=3))

    # 2. 영상 특유의 시네마틱 하단 다크 그라데이션 페이드 ("키우고 뒤에를 어둡게")
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grad)
    # gh_ratio: 최대 1.0 (100% 전체 높이까지 도달 가능)
    gh_ratio = max(0.1, min(1.0, float(grad_height) / 100.0))
    fade_start = int(h * (1.0 - gh_ratio))
    max_alpha = int(255 * max(0.0, min(1.0, float(grad_opacity) / 100.0)))

    fade_len = max(1, h - fade_start)
    for y in range(fade_start, h):
        ratio = (y - fade_start) / float(fade_len)
        # 텍스트 영역(하단부)에서 확실하게 묵직하고 짙은 검정색이 되도록 곡선 최적화 (ratio ** 0.65)
        # 하단 20% 지점부터는 max_alpha에 완전히 도달하여 글자가 선명하게 돋보이도록 함
        effective_ratio = min(1.0, (ratio ** 0.65) * 1.25)
        alpha = int(max_alpha * effective_ratio)
        g_draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    photo.paste(grad, (0, 0), grad)
    draw = ImageDraw.Draw(photo)

    # 3. 상단 로고 합성
    if logo_path and os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            lh = 36
            lw = int(logo_img.width * (lh / logo_img.height))
            if lw > 180:
                lw = 180
                lh = int(logo_img.height * (lw / logo_img.width))
            logo_img = logo_img.resize((lw, lh), Image.Resampling.LANCZOS)
            ly = 45
            lx = 65 if logo_position == "left" else ((w - lw) // 2 if logo_position == "center" else w - lw - 65)
            photo.paste(logo_img, (lx, ly), logo_img)
        except Exception:
            pass
    elif logo_text and logo_text.strip():
        logo_font = get_sub_font(28, bold=True)
        ly = 50
        lx = 65 if logo_position == "left" else (w // 2 if logo_position == "center" else w - 65)
        anchor = "la" if logo_position == "left" else ("mm" if logo_position == "center" else "ra")
        draw.text((lx, ly), logo_text.strip(), font=logo_font, fill=(255, 255, 255, 220), anchor=anchor)

    # 4. 하단 2줄 볼드 화이트 헤드라인
    clean_title = clean_pillow_text(title)
    headline_font = get_headline_font(size=font_size, weight=font_weight)
    max_text_w = w - 140

    if "\n" in clean_title:
        lines = [l.strip() for l in clean_title.split("\n") if l.strip()][:2]
    else:
        lines = wrap_text(clean_title, headline_font, max_text_w, draw)[:2]

    line_spacing = int(font_size * 1.30)
    total_title_h = len(lines) * line_spacing
    title_start_y = h - total_title_h - 75 + offset_y
    title_start_x = 70 + offset_x

    for idx, line in enumerate(lines):
        y_pos = title_start_y + (idx * line_spacing)
        # 묵직하고 깔끔한 소프트 그림자
        for dx, dy in [(1, 1), (1, 2), (2, 1), (2, 2)]:
            draw.text((title_start_x + dx, y_pos + dy), line, font=headline_font, fill=(0, 0, 0, 210))
        draw.text((title_start_x, y_pos), line, font=headline_font, fill=(255, 255, 255))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    photo.convert("RGB").save(output_path, "JPEG", quality=98)
    return str(output_path)

def create_story_slide(
    output_path: Path,
    title: str,
    story_points: list,
    logo_text: str = "",
    target_aspect: str = "1:1"
) -> str:
    """
    [2번 슬라이드] 영상의 두 번째 썸네일(사연/내용 설명 카드) 생성
    - 가독성 높은 미니멀 화이트 카드 배경
    - 헤드라인 및 불렛 포인트 4줄
    - 하단 저장/공유 유도 콜투액션
    """
    w, h = (1080, 1080) if target_aspect == "1:1" else (1080, 1350)
    card = Image.new("RGB", (w, h), (248, 249, 250))
    draw = ImageDraw.Draw(card)

    # 상단 로고 (텍스트가 있을 때만 표시)
    if logo_text and logo_text.strip():
        logo_font = get_sub_font(26, bold=True)
        draw.text((w // 2, 55), logo_text.strip(), font=logo_font, fill=(108, 117, 125), anchor="mm")

    # 제목
    t_font = get_headline_font(44)
    clean_title = clean_pillow_text(title.replace("\n", " "))
    title_lines = wrap_text(clean_title, t_font, w - 160, draw)[:2]
    cur_y = 130
    for l in title_lines:
        draw.text((80, cur_y), l, font=t_font, fill=(20, 24, 33))
        cur_y += 62

    # 구분선
    cur_y += 18
    draw.line([(80, cur_y), (w - 80, cur_y)], fill=(222, 226, 230), width=2)
    cur_y += 45

    # 불렛 포인트
    body_font = get_sub_font(32, bold=True)
    for p in story_points[:4]:
        clean_p = clean_pillow_text(p)
        draw.ellipse([80, cur_y + 8, 96, cur_y + 24], fill=(255, 60, 80))
        lines = wrap_text(clean_p, body_font, w - 210, draw)
        for line in lines[:2]:
            draw.text((118, cur_y), line, font=body_font, fill=(33, 37, 41))
            cur_y += 48
        cur_y += 24

    # 하단 콜투액션 박스
    box_y = h - 150
    draw.rounded_rectangle([80, box_y, w - 80, box_y + 85], radius=12, fill=(20, 24, 33))
    cta_font = get_sub_font(28, bold=True)
    draw.text((w // 2, box_y + 42), "저장해두고 친구에게 공유해보세요 >", font=cta_font, fill=(255, 255, 255), anchor="mm")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(output_path, "JPEG", quality=98)
    return str(output_path)

def transform_and_composite(
    source_image_path: Path,
    output_path: Path,
    title: str,
    badge: str = "기적의 실화",
    logo_path: str = None,
    logo_position: str = "center",
    font_size: int = 66,
    target_aspect: str = "1:1",
    subtitle: str = "전세계 23만 명이 감동한 실화",
    lang: str = "ko"
) -> str:
    """호환성 유지를 위한 래퍼 함수 (기본으로 1번 커버 슬라이드 생성)"""
    return create_cover_slide(
        source_image_path=source_image_path,
        output_path=output_path,
        title=title,
        logo_text="",
        logo_path=logo_path,
        logo_position=logo_position,
        font_size=font_size,
        target_aspect=target_aspect
    )

