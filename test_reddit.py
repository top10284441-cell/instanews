import requests
import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.boredpanda.com/animals/feed/'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
res = requests.get(url, headers=headers, timeout=10)

root = ET.fromstring(res.content)
channel = root.find('channel')
items = channel.findall('item')
print('Total BoredPanda Animals items:', len(items))

for it in items[:5]:
    title = it.find('title').text
    media = it.find('{http://search.yahoo.com/mrss/}content')
    img_url = media.attrib.get('url') if media is not None else None
    print(f"TITLE: {title}")
    print(f"IMAGE: {img_url}")
    print("-" * 50)
