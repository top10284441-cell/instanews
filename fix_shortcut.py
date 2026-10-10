# fix_shortcut.py
lines = [
    "@echo off",
    "title InstaBonus AI",
    'cd /d "D:\\사용자파일\\바탕화면\\antigravity\\instagrm_Auto"',
    "echo ================================================================",
    "echo   [InstaBonus AI] 인스타 보너스 수익화 자동화 시스템 시작",
    "echo ================================================================",
    "echo.",
    "python start_app.py",
    "pause"
]
target = r"D:\사용자파일\바탕화면\자동화 시작 바로가기\인스타_보너스_자동화(스마트폰연동).bat"
with open(target, "w", encoding="cp949") as f:
    f.write("\n".join(lines))
print("Shortcut batch file updated successfully!")
