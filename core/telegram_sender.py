import os
import sys
import requests
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def send_telegram_message(bot_token: str, chat_id: str, text: str) -> dict:
    """텔레그램 일반 텍스트 메시지 발송"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True
    }
    res = requests.post(url, json=payload, timeout=20)
    if res.status_code != 200:
        raise RuntimeError(f"텔레그램 메시지 발송 실패 ({res.status_code}): {res.text}")
    return res.json()

def send_telegram_photo(bot_token: str, chat_id: str, photo_path: str, caption: str = None) -> dict:
    """텔레그램 로컬 사진 직접 업로드 및 캡션 발송"""
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    data = {"chat_id": chat_id}
    
    # 텔레그램 사진 캡션 최대 1024자 제한 준수
    if caption:
        data["caption"] = caption[:1020]

    p = Path(photo_path)
    if not p.exists():
        raise FileNotFoundError(f"사진 파일을 찾을 수 없습니다: {photo_path}")

    with open(p, "rb") as f:
        files = {"photo": f}
        res = requests.post(url, data=data, files=files, timeout=40)

    if res.status_code != 200:
        raise RuntimeError(f"텔레그램 사진 발송 실패 ({res.status_code}): {res.text}")
    return res.json()

def send_card_to_telegram(bot_token: str, chat_id: str, post: dict, channel_name: str = "한국 야구") -> bool:
    """
    제작된 1장의 카드뉴스를 텔레그램으로 완벽하게 전송
    1) 고화질 표지 사진 전송
    2) 인스타그램에 그대로 복사해서 붙여넣을 수 있는 본문 텍스트 바로 아래 전송
    """
    try:
        # 슬라이드 1번 표지 이미지 경로 확보
        img_path = post.get("raw_image_path")
        if post.get("slides") and len(post["slides"]) > 0:
            slide_rel = post["slides"][0].lstrip("/")
            # 로컬 경로 복원
            possible_path = Path(post.get("raw_image_path", "")).parent / Path(slide_rel).name
            if possible_path.exists():
                img_path = str(possible_path)

        title = post.get("title", "")
        caption = post.get("caption", "")

        channel_emojis = {
            "한국 야구": "⚾",
            "한국 연예인": "⭐",
            "사건/이슈": "🚨",
            "동물/힐링": "🐾"
        }
        ch_emoji = channel_emojis.get(channel_name, "📰")
        photo_caption = f"{ch_emoji} [{channel_name}]\n🔥 {title}"
        
        # 1. 사진 전송 (요약 캡션 포함)
        send_telegram_photo(bot_token, chat_id, img_path, caption=photo_caption)

        # 2. 인스타 복사용 전체 본문 텍스트 전송 (글자 수 제한 없이 깔끔하게 복사 가능)
        copyable_text = f"📋 [인스타 본문 복사용 - {title}]\n━━━━━━━━━━━━━━━━━━━━\n{caption}"
        send_telegram_message(bot_token, chat_id, copyable_text)
        
        print(f"✅ 텔레그램 전송 완료: {title}")
        return True
    except Exception as e:
        print(f"❌ 텔레그램 전송 에러 ({post.get('title')}):", e)
        return False
