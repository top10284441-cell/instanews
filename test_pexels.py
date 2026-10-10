import requests
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.pexels.com/search/cute%20dog/'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
res = requests.get(url, headers=headers, timeout=10)
print('Pexels Status:', res.status_code)
imgs = re.findall(r'https://images\.pexels\.com/photos/\d+/[^\s"\'<>]+\.jpeg', res.text)
print('Found Pexels images:', len(imgs))
for img in list(set(imgs))[:5]:
    clean = img.split('?')[0] + '?auto=compress&cs=tinysrgb&w=1260&h=1260&dpr=2'
    print('High-res URL:', clean)
