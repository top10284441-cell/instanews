import os
import sys
import webbrowser
import threading
import time
import subprocess
import uvicorn
from config import LOCAL_IP, SERVER_PORT, SERVER_URL

def free_port(port):
    try:
        cmd = f'powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"'
        subprocess.run(cmd, shell=True, capture_output=True)
    except Exception:
        pass

def open_browser():
    time.sleep(1.5)
    url = f"http://localhost:{SERVER_PORT}"
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for cp in chrome_paths:
        if os.path.exists(cp):
            try:
                subprocess.Popen([cp, url])
                return
            except Exception:
                pass
    try:
        os.startfile(url)
    except Exception:
        webbrowser.open(url)

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("=" * 65)
    print("      🚀 [InstaBonus AI] 인스타 보너스 자동화 스튜디오")
    print("=" * 65)
    print(f"  [PC 브라우저 접속] : http://localhost:{SERVER_PORT}")
    print(f"  [스마트폰 접속 주소] : {SERVER_URL}")
    print("=" * 65)
    print("  📱 스마트폰 접속 방법:")
    print(f"  1. 스마트폰과 PC가 같은 Wi-Fi에 연결되어 있는지 확인합니다.")
    print(f"  2. 스마트폰 카메라로 웹 화면 우측 상단 '폰 연결' QR 코드를 찍거나,")
    print(f"     모바일 브라우저에 {SERVER_URL} 을 입력하세요.")
    print("=" * 65)
    print("  서버 실행 중... (종료하려면 Ctrl+C 를 누르세요)\n")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("server:app", host="0.0.0.0", port=SERVER_PORT, log_level="info")

if __name__ == "__main__":
    main()
