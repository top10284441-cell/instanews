import requests
import re
import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.boredpanda.com/animals/feed/'
headers = {'User-Agent': 'Mozilla/5.0'}
res = requests.get(url, headers=headers, timeout=10)
root = ET.fromstring(res.content)
item = root.find('channel').findall('item')[0]
article_link = item.find('link').text
print('Article link:', article_link)

a_res = requests.get(article_link, headers=headers, timeout=10)
imgs = re.findall(r'https://static\.boredpanda\.com/blog/wp-content/uploads/[^"\'\s>]+\.(?:jpg|jpeg|png)', a_res.text)
# remove duplicates & filters
clean_imgs = []
for img in imgs:
    # Look for high res images, avoiding small icons or avatar
    if any(k in img for k in ['_720', '_800', '_1000', '_1200', '_raw']) or not any(k in img for k in ['_150', '_300', 'logo']):
        clean_imgs.append(img)

print('Found full-res images in article:', len(set(clean_imgs)))
for img in list(set(clean_imgs))[:5]:
    print(' -', img)
