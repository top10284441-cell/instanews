import requests
import re
from pathlib import Path

out_dir = Path("audio")
out_dir.mkdir(exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

searches = {
    "sports_energy.mp3": "https://pixabay.com/music/search/sport/",
    "trendy_star.mp3": "https://pixabay.com/music/search/trendy/"
}

for name, search_url in searches.items():
    dest = out_dir / name
    if dest.exists() and dest.stat().st_size > 100000:
        print(f"{name} already exists.")
        continue
    try:
        res = requests.get(search_url, headers=headers, timeout=10)
        # find audio urls
        matches = re.findall(r'https://cdn\.pixabay\.com/download/audio/[^\"]+\.mp3', res.text)
        if not matches:
            matches = re.findall(r'https://cdn\.pixabay\.com/audio/[^\"]+\.mp3', res.text)
        print(f"Found {len(matches)} tracks for {name}")
        for m in matches:
            try:
                r_audio = requests.get(m, headers=headers, timeout=10)
                if r_audio.status_code == 200 and len(r_audio.content) > 100000:
                    dest.write_bytes(r_audio.content)
                    print(f"Successfully saved {name} ({len(r_audio.content)} bytes)")
                    break
            except Exception as e:
                pass
    except Exception as e:
        print(f"Error for {name}:", e)
