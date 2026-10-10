import json
import os
from pathlib import Path
from config import BASE_DIR, get_channels
from core.instagram_publisher import publish_to_instagram

QUEUE_FILE = BASE_DIR / "queue.json"

def load_queue() -> list:
    if not QUEUE_FILE.exists():
        return []
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_queue(queue: list):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

def add_posts_to_queue(new_posts: list) -> list:
    queue = load_queue()
    # 최신 포스팅이 위로 오도록 앞에 추가
    queue = new_posts + queue
    save_queue(queue)
    return queue

def update_post_status(post_id: str, status: str, extra: dict = None):
    queue = load_queue()
    for item in queue:
        if item.get("id") == post_id:
            item["status"] = status
            if extra:
                item.update(extra)
            break
    save_queue(queue)
    return queue

def approve_and_publish_post(post_id: str, channel_id: str = "default") -> dict:
    """사용자가 승인 누르면 인스타그램에 즉시 발행"""
    queue = load_queue()
    target_item = next((p for p in queue if p.get("id") == post_id), None)
    if not target_item:
        raise RuntimeError("승인할 포스팅을 찾을 수 없습니다.")

    channels = get_channels()
    target_channel_id = target_item.get("channel_id") or channel_id
    channel = next((c for c in channels if c["id"] == target_channel_id), None)
    if not channel:
        channel = next((c for c in channels if c["id"] == channel_id), None)
    if not channel:
        channel = channels[0] if channels else None
    if not channel:
        raise RuntimeError(f"채널을 찾을 수 없습니다: {channel_id}")

    # 슬라이드가 여러 장이면 캐러셀 전체 발행, 단일 장이면 단일 발행
    abs_img_list = []
    if target_item.get("slides") and len(target_item["slides"]) > 0:
        for s in target_item["slides"]:
            clean_s = str(s).split("?")[0]
            rel = clean_s.lstrip("/").replace("/", os.sep)
            p = BASE_DIR / rel
            if p.exists():
                abs_img_list.append(p)
    
    if not abs_img_list and target_item.get("image_url"):
        clean_url = str(target_item["image_url"]).split("?")[0]
        rel_img = clean_url.lstrip("/").replace("/", os.sep)
        abs_img = BASE_DIR / rel_img
        if abs_img.exists():
            abs_img_list.append(abs_img)

    if not abs_img_list:
        raise RuntimeError("발행할 슬라이드 이미지 파일이 존재하지 않습니다.")
    # 카드뉴스 사진 캐러셀(슬라이드)로 인스타그램 게시물 발행
    pub_res = publish_to_instagram(
        image_paths=abs_img_list,
        caption=target_item["caption"],
        account_id=channel["account_id"],
        access_token=channel["token"],
        folder=channel.get("cloudinary_folder")
    )

    update_post_status(
        post_id=post_id,
        status="approved",
        extra={
            "published_at": pub_res.get("post_id"),
            "post_url": pub_res.get("post_url")
        }
    )
    return pub_res

def reject_post(post_id: str):
    return update_post_status(post_id, "rejected")

def delete_post_item(post_id: str):
    queue = load_queue()
    queue = [p for p in queue if p.get("id") != post_id]
    save_queue(queue)
    return queue
