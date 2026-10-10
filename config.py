import os
import socket
import csv
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

def get_local_ip():
    """스마트폰 접속을 위한 현재 PC의 로컬 네트워크 IP 감지"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
SERVER_PORT = 8555
SERVER_URL = f"http://{LOCAL_IP}:{SERVER_PORT}"

# API Keys & Meta Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "instagram_bonus_auto")

DEFAULT_INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
DEFAULT_META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_GRAPH_BASE = os.getenv("META_GRAPH_BASE", "https://graph.instagram.com")
META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v25.0")

OUTPUT_DIR = BASE_DIR / "output"
SOURCE_DIR = BASE_DIR / "source_images"
LOGO_DIR = BASE_DIR / "logos"
CHANNELS_CSV = BASE_DIR / "channels.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_DIR.mkdir(parents=True, exist_ok=True)
LOGO_DIR.mkdir(parents=True, exist_ok=True)

def get_channels():
    """등록된 인스타그램 계정 채널 목록 로드"""
    channels = [
        {
            "id": "default",
            "name": "기본 계정 (Default)",
            "account_id": DEFAULT_INSTAGRAM_ACCOUNT_ID,
            "token": DEFAULT_META_ACCESS_TOKEN,
            "cloudinary_folder": CLOUDINARY_FOLDER
        }
    ]
    if CHANNELS_CSV.exists():
        try:
            with open(CHANNELS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ch_key = row.get("channel", "").strip()
                    display_name = row.get("display_name", ch_key).strip()
                    acc_env = row.get("instagram_account_id_env", "").strip()
                    tok_env = row.get("meta_access_token_env", "").strip()
                    c_folder = row.get("cloudinary_folder", CLOUDINARY_FOLDER).strip()
                    
                    acc_id = os.getenv(acc_env, DEFAULT_INSTAGRAM_ACCOUNT_ID) if acc_env else DEFAULT_INSTAGRAM_ACCOUNT_ID
                    token = os.getenv(tok_env, DEFAULT_META_ACCESS_TOKEN) if tok_env else DEFAULT_META_ACCESS_TOKEN
                    
                    if ch_key and ch_key != "default":
                        channels.append({
                            "id": ch_key,
                            "name": display_name,
                            "account_id": acc_id,
                            "token": token,
                            "cloudinary_folder": c_folder
                        })
        except Exception as e:
            print("Error loading channels.csv:", e)
    return channels
