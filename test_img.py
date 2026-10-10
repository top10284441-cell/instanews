import requests, xml.etree.ElementTree as ET, re, sys

res = requests.get('https://www.chosun.com/arc/outboundfeeds/rss/category/sports/?outputType=xml')
root = ET.fromstring(res.content)

def get_og_image(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if r.status_code == 200:
            m = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', r.text)
            if not m:
                m = re.search(r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']', r.text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None

team_candidates = {}
for it in root.findall('.//item'):
    t = (it.find('title').text or '').strip()
    l = (it.find('link').text or '').strip()
    if '/sports/baseball/' not in l or t.startswith('[포토]') or t.startswith('[사진]'):
        continue
    if any(no in t for no in ['드래프트', '신인 선수', '계약 완료', '라밤바', '등록', '말소', '1군 등록', 'FA']):
        continue

    matched = None
    for tm in ['KIA', '기아', '삼성', '두산', '한화', 'SSG', '롯데', 'NC', 'KT', '키움', 'LG']:
        if tm in t:
            matched = 'KIA' if tm in ('KIA', '기아') else tm
            break
    if not matched:
        matched = '기타'

    if matched not in team_candidates:
        team_candidates[matched] = []

    media = it.find('{http://search.yahoo.com/mrss/}content') or it.find('{http://search.yahoo.com/mrss/}thumbnail')
    img_url = media.attrib.get('url') if media is not None else None

    team_candidates[matched].append({'title': t, 'link': l, 'img_url': img_url})

# 구단별로 1개씩 선별하여 고화질 이미지 보장
picked_teams = ['KIA', '삼성', '두산', 'SSG', '한화', '롯데', 'NC', 'KT', 'LG']
final_cards = []

for tm in picked_teams:
    if tm in team_candidates and team_candidates[tm]:
        top_art = team_candidates[tm][0]
        img = top_art['img_url']
        if not img:
            img = get_og_image(top_art['link'])
        if img:
            final_cards.append((tm, top_art['title'], img))
        if len(final_cards) >= 3:
            break

for tm, title, img in final_cards:
    sys.stdout.buffer.write((f'[{tm}]: {title[:40]} | IMG: {img[:35]}...\n').encode('utf-8'))
