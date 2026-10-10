import re
import requests
from pathlib import Path
from datetime import datetime
import json
from core.image_transformer import create_cover_slide, create_story_slide

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 1. 야구/스포츠 고화질 사진 수집
print("Fetching sports photo...")
res_sp = requests.get('https://www.pexels.com/search/baseball%20game/', headers=headers, timeout=12)
sp_imgs = list(set(re.findall(r'https://images\.pexels\.com/photos/\d+/[^\s"\'<>]+\.jpeg', res_sp.text)))
sp_url = sp_imgs[0].split('?')[0] + '?auto=compress&cs=tinysrgb&w=1080&h=1080&fit=crop' if sp_imgs else None
sports_raw = Path('real_sports_clean.jpg')
if sp_url:
    with open(sports_raw, 'wb') as f:
        f.write(requests.get(sp_url, headers=headers).content)
    print("Sports photo saved:", sports_raw)

# 2. 정치/시사 뉴스 고화질 사진 수집
print("Fetching news photo...")
res_nw = requests.get('https://www.pexels.com/search/politics%20conference/', headers=headers, timeout=12)
nw_imgs = list(set(re.findall(r'https://images\.pexels\.com/photos/\d+/[^\s"\'<>]+\.jpeg', res_nw.text)))
nw_url = nw_imgs[0].split('?')[0] + '?auto=compress&cs=tinysrgb&w=1080&h=1080&fit=crop' if nw_imgs else None
news_raw = Path('real_news_clean.jpg')
if nw_url:
    with open(news_raw, 'wb') as f:
        f.write(requests.get(nw_url, headers=headers).content)
    print("News photo saved:", news_raw)

# 3. 렌더링
p_sp_1 = Path('output/sports_showcase/slide1.jpg')
p_sp_2 = Path('output/sports_showcase/slide2.jpg')
p_nw_1 = Path('output/news_showcase/slide1.jpg')
p_nw_2 = Path('output/news_showcase/slide2.jpg')
p_sp_1.parent.mkdir(parents=True, exist_ok=True)
p_nw_1.parent.mkdir(parents=True, exist_ok=True)

create_cover_slide(
    source_image_path=sports_raw,
    output_path=p_sp_1,
    title='‘역전 결승포 폭발!’\n9회말에 갈린 기적의 승부',
    logo_text='',
    target_aspect='1:1'
)
create_story_slide(
    output_path=p_sp_2,
    title='‘역전 결승포 폭발!’ 9회말에 갈린 기적의 승부',
    story_points=[
        '경기 내내 팽팽하던 승부, 9회말 2사에서 터진 극적인 한 방',
        '팬들의 함성이 경기장을 뒤흔든 시즌 최고의 명장면 탄생',
        '감독과 선수단 모두 부둥켜안으며 승리의 기쁨을 나눴습니다',
        '치열한 순위 싸움 속 팀 분위기를 단번에 반전시킨 결정적 1승'
    ],
    logo_text='',
    target_aspect='1:1'
)

create_cover_slide(
    source_image_path=news_raw,
    output_path=p_nw_1,
    title='‘정치권 초미의 관심사’\n오늘 긴급 발표된 핵심 쟁점 3가지',
    logo_text='',
    target_aspect='1:1'
)
create_story_slide(
    output_path=p_nw_2,
    title='‘정치권 초미의 관심사’ 오늘 긴급 발표된 핵심 쟁점 3가지',
    story_points=[
        '여야 긴급 회동 끝에 나온 이번 발표의 실질적 핵심 내용',
        '국민 생활과 직결된 법안 개정안을 둘러싼 치열한 공방',
        '전문가들이 전망하는 향후 정국 변화와 입법 일정 시나리오',
        '사건과 이슈의 흐름을 한 장으로 쉽고 명확하게 정리했습니다'
    ],
    logo_text='',
    target_aspect='1:1'
)

# 4. queue.json 저장
queue = [
    {
        'id': 'post_sports_miracle',
        'category': '스포츠 게시물',
        'title': '‘역전 결승포 폭발!’ 9회말에 갈린 기적의 승부',
        'caption': '‘역전 결승포 폭발!’ 9회말 2사에 터진 각본 없는 드라마 ⚾🔥\n\n치열했던 경기 끝에 터진 결정적인 한 방으로 경기장이 열광의 도가니에 빠졌습니다.\n\n스포츠가 주는 짜릿한 감동을 확인해 보세요!\n\n#프로야구 #홈런 #역전승 #야구스타그램 #명승부 #오늘의스포츠',
        'image_url': '/output/sports_showcase/slide1.jpg',
        'slides': ['/output/sports_showcase/slide1.jpg', '/output/sports_showcase/slide2.jpg'],
        'active_slide': 0,
        'lang': 'ko',
        'status': 'pending',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    },
    {
        'id': 'post_news_urgent',
        'category': '사건으로 보는 오늘',
        'title': '‘정치권 초미의 관심사’ 오늘 긴급 발표된 핵심 쟁점 3가지',
        'caption': '오늘 정치권과 사회를 뜨겁게 달군 핵심 쟁점 한눈에 보기 📰⚖️\n\n주요 현안과 앞으로의 쟁점 사항을 4줄 요약으로 쉽고 정확하게 전해드립니다.\n\n#시사뉴스 #정치이슈 #오늘의사건 #이슈정리 #뉴스카드 #사건으로보는오늘',
        'image_url': '/output/news_showcase/slide1.jpg',
        'slides': ['/output/news_showcase/slide1.jpg', '/output/news_showcase/slide2.jpg'],
        'active_slide': 0,
        'lang': 'ko',
        'status': 'pending',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
]

with open('queue.json', 'w', encoding='utf-8') as f:
    json.dump(queue, f, ensure_ascii=False, indent=2)

print("Done! Both posts ready in queue.")
