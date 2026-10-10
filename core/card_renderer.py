import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_KR_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_KR_REGULAR = r"C:\Windows\Fonts\malgun.ttf"
FONT_JP = r"C:\Windows\Fonts\msgothic.ttc"
FONT_EN = r"C:\Windows\Fonts\arial.ttf"

def get_font(size: int, bold: bool = True, lang: str = "ko"):
    if lang == "ja" and os.path.exists(FONT_JP):
        font_path = FONT_JP
    elif bold and os.path.exists(FONT_KR_BOLD):
        font_path = FONT_KR_BOLD
    elif os.path.exists(FONT_KR_REGULAR):
        font_path = FONT_KR_REGULAR
    else:
        font_path = FONT_EN
    return ImageFont.truetype(font_path, size)

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
    """텍스트를 주어진 너비에 맞게 자동 줄바꿈"""
    lines = []
    paragraphs = text.split("\n")
    for para in paragraphs:
        if not para.strip():
            lines.append("")
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
                    # 단어 하나가 너무 길 경우 문자 단위 분할
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

def create_gradient_background(width: int, height: int, style: str = "dark_modern") -> Image.Image:
    """고급스러운 배경 그라데이션 이미지 생성"""
    base = Image.new("RGB", (width, height), (15, 17, 23))
    draw = ImageDraw.Draw(base)
    
    if style == "gradient_sunset":
        top_color = (24, 18, 43)
        bottom_color = (60, 20, 35)
    elif style == "cyber_blue":
        top_color = (10, 20, 38)
        bottom_color = (15, 35, 55)
    else: # dark_modern
        top_color = (18, 22, 34)
        bottom_color = (10, 12, 18)
        
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    # 부드러운 네온 글로우 원형 효과 추가
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    if style == "gradient_sunset":
        g_draw.ellipse([width//3, -100, width + 100, height//2], fill=(255, 107, 107, 45))
    else:
        g_draw.ellipse([width//4, -50, width + 200, height//2], fill=(79, 128, 255, 35))
        g_draw.ellipse([-100, height//2, width//2, height + 100], fill=(138, 43, 226, 30))
    
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    base.paste(glow, (0, 0), glow)
    return base

def render_card_slide(
    slide_data: dict,
    total_slides: int,
    output_path: Path,
    bg_image_path: str = None,
    width: int = 1080,
    height: int = 1350,
    theme: str = "dark_modern",
    lang: str = "ko"
):
    """
    개별 카드뉴스 슬라이드 렌더링
    slide_data: {
        "index": 1,
        "is_cover": True,
        "badge": "💡 알면 돈되는 꿀팁",
        "title": "부자들의 5가지 아침 습관",
        "body": "본문 내용이 들어갑니다...",
        "footer_tip": "옆으로 넘겨서 확인 👉"
    }
    """
    is_cover = slide_data.get("is_cover", False)
    index = slide_data.get("index", 1)
    badge = slide_data.get("badge", "")
    title = slide_data.get("title", "")
    body = slide_data.get("body", "")
    footer_tip = slide_data.get("footer_tip", "")
    
    # 1. 배경 준비
    if bg_image_path and os.path.exists(bg_image_path):
        try:
            img = Image.open(bg_image_path).convert("RGB")
            # 비율 유지 채우기 (Aspect Fill)
            img_ratio = img.width / img.height
            target_ratio = width / height
            if img_ratio > target_ratio:
                new_w = int(img.height * target_ratio)
                left = (img.width - new_w) // 2
                img = img.crop((left, 0, left + new_w, img.height))
            else:
                new_h = int(img.width / target_ratio)
                top = (img.height - new_h) // 2
                img = img.crop((0, top, img.width, top + new_h))
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            # 가독성을 위한 어두운 오버레이 레이어
            overlay = Image.new("RGBA", (width, height), (10, 12, 18, 195 if is_cover else 215))
            img.paste(overlay, (0, 0), overlay)
        except Exception:
            img = create_gradient_background(width, height, theme)
    else:
        img = create_gradient_background(width, height, theme)
        
    draw = ImageDraw.Draw(img)
    margin_x = 90
    max_text_w = width - (margin_x * 2)

    # 2. 커버 슬라이드 렌더링
    if is_cover:
        current_y = 220
        # 상단 뱃지
        if badge:
            badge_font = get_font(36, bold=True, lang=lang)
            bbox = draw.textbbox((0, 0), badge, font=badge_font)
            bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
            pad_x, pad_y = 30, 14
            badge_rect = [margin_x, current_y, margin_x + bw + pad_x * 2, current_y + bh + pad_y * 2]
            # 라운드 뱃지 박스
            draw.rounded_rectangle(badge_rect, radius=20, fill=(255, 215, 0, 240) if theme != "gradient_sunset" else (255, 90, 95))
            draw.text((margin_x + pad_x, current_y + pad_y - 3), badge, font=badge_font, fill=(15, 15, 20))
            current_y += bh + pad_y * 2 + 70
        else:
            current_y += 50
            
        # 메인 후킹 타이틀 (큰 볼드 폰트)
        title_font = get_font(72, bold=True, lang=lang)
        title_lines = wrap_text(title, title_font, max_text_w, draw)
        line_height = 98
        
        for line in title_lines:
            # 텍스트 그림자
            draw.text((margin_x + 3, current_y + 3), line, font=title_font, fill=(0, 0, 0, 180))
            draw.text((margin_x, current_y), line, font=title_font, fill=(255, 255, 255))
            current_y += line_height
            
        current_y += 40
        # 부제목 / 본문 요약
        if body:
            body_font = get_font(42, bold=False, lang=lang)
            body_lines = wrap_text(body, body_font, max_text_w, draw)
            b_height = 62
            for line in body_lines:
                draw.text((margin_x, current_y), line, font=body_font, fill=(210, 215, 225))
                current_y += b_height

        # 하단 가이드 문구
        guide_text = footer_tip or "옆으로 넘겨서 확인 👉"
        guide_font = get_font(36, bold=True, lang=lang)
        g_bbox = draw.textbbox((0, 0), guide_text, font=guide_font)
        gw = g_bbox[2] - g_bbox[0]
        bottom_y = height - 160
        # 둥근 버튼 형태 가이드
        g_box = [(width - gw)//2 - 35, bottom_y - 12, (width + gw)//2 + 35, bottom_y + 52]
        draw.rounded_rectangle(g_box, radius=30, fill=(255, 255, 255, 30), outline=(255, 255, 255, 70), width=2)
        draw.text(((width - gw)//2, bottom_y), guide_text, font=guide_font, fill=(255, 230, 100))

    # 3. 본문 슬라이드 렌더링
    else:
        # 상단 번호 인디케이터 (예: 01, 02)
        top_num = f"{index:02d}"
        num_font = get_font(52, bold=True, lang=lang)
        draw.text((margin_x, 150), top_num, font=num_font, fill=(255, 215, 0))
        
        # 상단 얇은 분할선
        draw.line([(margin_x, 225), (width - margin_x, 225)], fill=(255, 255, 255, 50), width=2)
        
        current_y = 280
        # 슬라이드 소제목
        if title:
            sub_font = get_font(60, bold=True, lang=lang)
            sub_lines = wrap_text(title, sub_font, max_text_w, draw)
            for line in sub_lines:
                draw.text((margin_x, current_y), line, font=sub_font, fill=(255, 255, 255))
                current_y += 82
            current_y += 40
            
        # 슬라이드 본문 텍스트
        body_font = get_font(42, bold=False, lang=lang)
        body_lines = wrap_text(body, body_font, max_text_w, draw)
        for line in body_lines:
            draw.text((margin_x, current_y), line, font=body_font, fill=(225, 230, 240))
            current_y += 66
            
        # 하단 페이지 표시 (예: 2 / 5)
        page_str = f"{index} / {total_slides}"
        page_font = get_font(34, bold=True, lang=lang)
        p_bbox = draw.textbbox((0, 0), page_str, font=page_font)
        pw = p_bbox[2] - p_bbox[0]
        draw.text((width - margin_x - pw, height - 140), page_str, font=page_font, fill=(150, 160, 175))
        
        # 하단 계정 브랜드명 / 팁
        if footer_tip:
            f_font = get_font(32, bold=False, lang=lang)
            draw.text((margin_x, height - 140), footer_tip, font=f_font, fill=(160, 170, 185))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    return str(output_path)
