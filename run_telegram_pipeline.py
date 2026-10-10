#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Actions 및 독립 실행용 텔레그램 자동 발송 파이프라인
채널당 15개의 최신 바이럴/경기 카드뉴스를 자동 생성하여 텔레그램으로 전송합니다.
"""

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from dotenv import load_dotenv

# .env 로드 (로컬 테스트용)
load_dotenv()

from config import OPENAI_API_KEY
from core.auto_curator import auto_generate_curated_posts
from core.telegram_sender import send_card_to_telegram

CHANNEL_NAMES = {
    "baseball": "한국 야구",
    "celebrity": "한국 연예인",
    "today_events": "사건/이슈",
    "animals": "동물/힐링"
}

def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    openai_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY)

    if not openai_key:
        print("❌ [오류] OPENAI_API_KEY 가 설정되지 않았습니다.")
        sys.exit(1)

    if not bot_token or not chat_id:
        print("❌ [오류] TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 가 설정되지 않았습니다.")
        print("   GitHub 저장소 Settings -> Secrets and variables -> Actions 에 등록하거나 .env에 입력해 주세요.")
        sys.exit(1)

    # 발송할 채널 목록 (4대 채널 기본: baseball, celebrity, today_events, animals)
    target_channels_raw = os.getenv("TARGET_CHANNELS", "baseball,celebrity,today_events,animals")
    target_channels = [c.strip() for c in target_channels_raw.split(",") if c.strip()]

    # 1회 실행 시 채널당 생성 개수 (아침 5개, 저녁 5개 -> 하루 총 10개 x 4채널 = 40개)
    try:
        count_per_channel = int(os.getenv("COUNT_PER_CHANNEL", "5"))
    except ValueError:
        count_per_channel = 5

    print("=" * 60)
    print("🚀 [InstaBonus AI] 텔레그램 자동 발송 파이프라인 가동")
    print(f"📌 대상 채널: {', '.join(target_channels)}")
    print(f"📊 채널당 목표 생성 수: {count_per_channel}장")
    print("=" * 60)

    total_sent = 0

    for ch in target_channels:
        ch_name = CHANNEL_NAMES.get(ch, ch)
        print(f"\n▶ [{ch_name} ({ch})] {count_per_channel}개 카드뉴스 자동 제작 시작...")

        try:
            posts = auto_generate_curated_posts(
                count=count_per_channel,
                channel_id=ch,
                lang="ko",
                logo_text=""
            )
            print(f"✨ [{ch_name}] {len(posts)}개 카드뉴스 제작 완료! 텔레그램 발송을 시작합니다.")

            for idx, post in enumerate(posts):
                success = send_card_to_telegram(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    post=post,
                    channel_name=ch_name
                )
                if success:
                    total_sent += 1
                # 텔레그램 API 속도 제한 방지 (1초 대기)
                time.sleep(1.2)

        except Exception as e:
            print(f"❌ [{ch_name}] 처리 중 오류 발생:", e)

    print("\n" + "=" * 60)
    print(f"🎉 모든 작업 완료! 총 {total_sent}개의 게시물이 텔레그램으로 성공적으로 전송되었습니다.")
    print("=" * 60)

if __name__ == "__main__":
    main()
