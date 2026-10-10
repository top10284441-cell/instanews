import json
import os
from openai import OpenAI
from pathlib import Path
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

SYSTEM_PROMPT = """
당신은 인스타그램 보너스 수익화(Instagram Bonus) 및 바이럴 카드뉴스 전문 마케터이자 AI 콘텐츠 기획자입니다.
인스타그램에서 사용자가 스와이프를 끝까지 넘기게 만드는 고체류/고도달 콘텐츠를 기획합니다.

입력된 주제와 언어에 맞추어 아래 JSON 형식으로만 응답해야 합니다. 마크다운 따옴표(```json) 없이 순수 JSON만 출력하세요.

JSON 출력 형식:
{
  "theme_badge": "💡 알면 돈되는 꿀팁 (카테고리 뱃지)",
  "cover": {
    "title": "호기심을 극대화하는 강력한 1줄 후킹 타이틀",
    "body": "타이틀을 보충하는 1~2줄의 흥미 유발 설명",
    "guide": "옆으로 넘겨서 확인 👉"
  },
  "slides": [
    {
      "index": 2,
      "title": "소제목 1",
      "body": "핵심 내용 3~4줄. 쉽고 간결하게 작성.",
      "footer_tip": "포인트 요약 또는 팁"
    },
    {
      "index": 3,
      "title": "소제목 2",
      "body": "핵심 내용 3~4줄. 쉽고 간결하게 작성.",
      "footer_tip": "포인트 요약 또는 팁"
    },
    {
      "index": 4,
      "title": "소제목 3",
      "body": "핵심 내용 3~4줄. 쉽고 간결하게 작성.",
      "footer_tip": "포인트 요약 또는 팁"
    },
    {
      "index": 5,
      "title": "마무리 & 여러분의 생각은?",
      "body": "저장해두고 필요할 때마다 꺼내보세요! 댓글로 여러분의 팁도 공유해주세요.",
      "footer_tip": "저장 & 팔로우 부탁드립니다 ❤️"
    }
  ],
  "caption": "인스타그램 본문에 들어갈 텍스트 (줄바꿈 포함)",
  "hashtags": ["#태그1", "#태그2", "#태그3", "#태그4", "#태그5"],
  "image_prompt": "DALL-E 또는 배경으로 어울리는 분위기 묘사 영어 프롬프트 (예: cinematic moody minimalist aesthetic backdrop, high quality)"
}
"""

def generate_card_content(topic: str, category: str = "꿀팁/정보", lang: str = "ko") -> dict:
    """주제와 언어에 맞춰 카드뉴스 콘텐츠 JSON 생성"""
    if not client:
        raise RuntimeError("OpenAI API 키가 설정되어 있지 않습니다 (.env 확인 필요).")

    lang_instructions = {
        "ko": "반드시 한국어로 자연스럽고 가독성 높게 작성하세요.",
        "ja": "반드시 자연스러운 일본어로 작성하세요. 일본 인스타그램 바이럴 문체(입니다/ます 체, 이모지 적절히)를 적용하고 일본 인기 해시태그를 포함하세요.",
        "en": "Write completely in English with engaging, catchy viral Instagram carousel copywriting and trending hashtags."
    }
    
    user_prompt = f"""
카테고리: {category}
주제: {topic}
언어: {lang} ({lang_instructions.get(lang, '한국어')})

위 주제로 인스타그램 보너스 프로그램에서 조회수와 완독률을 극대화할 수 있는 5장 구성의 카드뉴스 콘텐츠를 생성해 주세요.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    
    raw_text = response.choices[0].message.content
    data = json.loads(raw_text)
    return data

def translate_or_adapt_content(content_dict: dict, target_lang: str) -> dict:
    """기존 한국어 콘텐츠를 일본어나 영어로 현지화 변환"""
    if not client:
        raise RuntimeError("OpenAI API 키가 필요합니다.")
        
    prompt = f"""
다음 인스타그램 카드뉴스 JSON 데이터를 타겟 언어({target_lang})로 완벽하게 현지화 번역해 주세요.
직역하지 말고 해당 언어권 인스타그램에서 자연스럽게 읽히도록 세련되게 변환하세요.
해시태그도 해당 국가에서 유행하는 태그로 변경하세요.

원본 JSON:
{json.dumps(content_dict, ensure_ascii=False)}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional social media localizer. Output pure JSON matching the input schema."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def generate_ai_background(prompt: str, output_path: Path) -> str:
    """DALL-E 3를 이용한 AI 배경 생성 (선택 사항)"""
    if not client:
        return None
    try:
        import requests
        res = client.images.generate(
            model="dall-e-3",
            prompt=f"Aesthetic backdrop for Instagram post, minimalist, cinematic, {prompt}, no text, no letters, clean background",
            size="1024x1024",
            quality="standard",
            n=1
        )
        img_url = res.data[0].url
        img_data = requests.get(img_url, timeout=30).content
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img_data)
        return str(output_path)
    except Exception as e:
        print("DALL-E generation error:", e)
        return None
