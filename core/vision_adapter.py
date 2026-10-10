import base64
import json
from pathlib import Path
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def analyze_and_adapt_image(image_path: Path, lang: str = "ko") -> dict:
    """
    캡처된 이미지를 GPT-4o Vision으로 분석하여
    1. 이미지 내용 및 원본 글자 파악
    2. 클릭률을 극대화하는 후킹 썸네일 제목 창작
    3. 인스타 본문용 매거진/스토리텔링 각색 본문 생성
    4. 타겟 언어(한국어/일본어/영어) 맞춤 생성
    """
    if not client:
        raise RuntimeError("OpenAI API 키가 필요합니다.")

    b64_img = encode_image(image_path)
    ext = image_path.suffix.lower().replace(".", "")
    mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"

    lang_guide = {
        "ko": "한국어로 작성하세요. 인스타그램에서 반응과 체류 시간을 폭발시키는 매거진/썰 스타일.",
        "ja": "일본어로 작성하세요. 일본 인스타그램 바이럴 문체(입니다/ます체, 이모지) 및 일본 현지 인기 해시태그 포함.",
        "en": "Write in English with catchy, viral Instagram magazine/storytelling tone and trending hashtags."
    }

    prompt = f"""
당신은 인스타그램 보너스 수익화 및 100만 조회수 전문 바이럴 에디터입니다.
첨부된 캡처 이미지를 분석하고 원본 내용을 바탕으로 인스타그램에 올릴 수 있도록 새롭게 각색해 주세요.

목표 언어: {lang} ({lang_guide.get(lang, '한국어')})

반드시 아래 JSON 형식으로만 답변하세요:
{{
  "hooking_title": "이미지 위에 크게 얹을 1~2줄의 강력한 후킹 제목 (짧고 호기심을 자극)",
  "caption": "인스타 본문에 들어갈 상세 각색 글 (원본의 내용을 자연스럽게 살려 재구성)",
  "hashtags": ["#해시태그1", "#해시태그2", "#해시태그3", "#해시태그4", "#해시태그5"]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_img}",
                            "detail": "low"
                        }
                    }
                ]
            }
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    result_json = json.loads(response.choices[0].message.content)
    return result_json
