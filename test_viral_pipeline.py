import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from openai import OpenAI
from config import OPENAI_API_KEY
from core.image_transformer import transform_and_composite
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
client = OpenAI(api_key=OPENAI_API_KEY)

# 1. BoredPanda 실시간 바이럴 피드에서 1위 스토리와 실제 사진 가져오기
url = 'https://www.boredpanda.com/animals/feed/'
headers = {'User-Agent': 'Mozilla/5.0'}
res = requests.get(url, headers=headers, timeout=10)
root = ET.fromstring(res.content)
item = root.find('channel').findall('item')[0]

raw_title = item.find('title').text
media = item.find('{http://search.yahoo.com/mrss/}content')
img_url = media.attrib.get('url') if media is not None else None

print('Original Viral Story:', raw_title)
print('Original Real Photo:', img_url)

# 2. 실제 고화질 사진 다운로드
img_data = requests.get(img_url, timeout=15).content
raw_img_path = Path('output/viral_test_raw.jpg')
raw_img_path.parent.mkdir(parents=True, exist_ok=True)
with open(raw_img_path, 'wb') as f:
    f.write(img_data)

# 3. GPT-4o로 한국어 후킹 제목 및 매거진 스토리 각색
prompt = f"""
다음은 해외 SNS에서 조회수와 공감이 폭발한 실시간 화제의 동물 실화입니다:
"{raw_title}"

이 실제 스토리를 바탕으로 인스타그램에서 100만 조회가 터질 수 있는 한국어 포스팅을 기획해 주세요.
반드시 아래 JSON 형식으로 응답하세요:
{{
  "badge": "🐾 기적의 동물 실화",
  "hooking_title": "1줄 상황 제시\\n2줄 충격/감동 포인트 (줄바꿈 포함 2줄)",
  "caption": "인스타 본문에 들어갈 4~6줄의 몰입감 넘치는 감동 매거진 스토리 (이모지 포함)",
  "hashtags": ["#감동실화", "#유기견구조", "#반려동물", "#기적같은순간", "#인스타툰"]
}}
"""

res_ai = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)

ai_data = json.loads(res_ai.choices[0].message.content)
print('AI Hooking Title:\n', ai_data['hooking_title'])

# 4. 프로급 1:1 카드뉴스 자동 렌더링
final_card_path = Path('output/viral_test_card.jpg')
transform_and_composite(
    source_image_path=raw_img_path,
    output_path=final_card_path,
    title=ai_data['hooking_title'],
    badge=ai_data['badge'],
    font_size=56,
    gradient_darkness=70,
    target_aspect="1:1",
    lang="ko"
)

print('SUCCESS! Final Card Created at:', final_card_path)
