import hashlib
import time
from pathlib import Path
import requests
from config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_FOLDER,
    DEFAULT_INSTAGRAM_ACCOUNT_ID,
    DEFAULT_META_ACCESS_TOKEN,
    META_GRAPH_BASE,
    META_GRAPH_VERSION
)

def graph_endpoint(path: str) -> str:
    base = META_GRAPH_BASE.rstrip("/")
    version = META_GRAPH_VERSION.strip("/")
    return f"{base}/{version}/{path.lstrip('/')}"

def cloudinary_signature(params: dict, secret: str) -> str:
    serialized = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return hashlib.sha1(f"{serialized}{secret}".encode("utf-8")).hexdigest()

def upload_to_cloudinary(image_path: Path, folder: str = None) -> str:
    """로컬 이미지를 Cloudinary에 업로드하여 공개 URL 반환"""
    if not CLOUDINARY_CLOUD_NAME or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
        raise RuntimeError("Cloudinary 설정이 누락되었습니다 (.env 확인 필요).")
        
    target_folder = folder or CLOUDINARY_FOLDER
    timestamp = int(time.time())
    params = {"folder": target_folder, "timestamp": timestamp}
    sig = cloudinary_signature(params, CLOUDINARY_API_SECRET)
    
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
    with open(image_path, "rb") as f:
        res = requests.post(
            url,
            data={
                "api_key": CLOUDINARY_API_KEY,
                "timestamp": timestamp,
                "folder": target_folder,
                "signature": sig,
            },
            files={"file": f},
            timeout=120,
        )
    if res.status_code >= 400:
        raise RuntimeError(f"Cloudinary 업로드 실패: {res.text}")
    return res.json()["secure_url"]

def upload_video_to_cloudinary(video_path: Path, folder: str = None) -> str:
    """로컬 MP4 비디오를 Cloudinary에 업로드하여 공개 URL 반환"""
    if not CLOUDINARY_CLOUD_NAME or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
        raise RuntimeError("Cloudinary 설정이 누락되었습니다 (.env 확인 필요).")
        
    target_folder = folder or f"{CLOUDINARY_FOLDER}/reels"
    timestamp = int(time.time())
    sig_params = {"folder": target_folder, "timestamp": timestamp}
    sig = cloudinary_signature(sig_params, CLOUDINARY_API_SECRET)
    
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/video/upload"
    with open(video_path, "rb") as f:
        res = requests.post(
            url,
            data={
                "api_key": CLOUDINARY_API_KEY,
                "timestamp": timestamp,
                "folder": target_folder,
                "signature": sig,
            },
            files={"file": f},
            timeout=180,
        )
    if res.status_code >= 400:
        raise RuntimeError(f"Cloudinary 비디오 업로드 실패: {res.text}")
    return res.json()["secure_url"]

def publish_reel_to_instagram(
    video_path: Path,
    caption: str,
    account_id: str = None,
    access_token: str = None,
    folder: str = None
) -> dict:
    """
    배경음악(BGM)이 합성된 7초 릴스 비디오를 인스타그램 릴스 & 피드에 자동 발행
    """
    target_acc = account_id or DEFAULT_INSTAGRAM_ACCOUNT_ID
    target_tok = access_token or DEFAULT_META_ACCESS_TOKEN
    
    if not target_acc or not target_tok:
        raise RuntimeError("Instagram 계정 ID 또는 Meta 액세스 토큰이 없습니다.")
        
    # 1. Cloudinary에 비디오 업로드
    video_url = upload_video_to_cloudinary(Path(video_path), folder)

    # 2. 인스타그램 릴스 컨테이너 생성 (피드에도 동시 노출: share_to_feed=true)
    create_url = graph_endpoint(f"{target_acc}/media")
    res = requests.post(
        create_url,
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": target_tok
        },
        timeout=90
    )
    if res.status_code >= 400:
        raise RuntimeError(f"릴스 컨테이너 생성 실패: {res.text}")
    container_id = res.json()["id"]

    # 3. 비디오 인코딩 대기
    wait_for_container(container_id, target_tok, max_wait=60)

    # 4. 최종 발행
    pub_url = graph_endpoint(f"{target_acc}/media_publish")
    pub_res = requests.post(
        pub_url,
        data={"creation_id": container_id, "access_token": target_tok},
        timeout=60
    )
    if pub_res.status_code >= 400:
        raise RuntimeError(f"릴스 최종 발행 실패: {pub_res.text}")
        
    post_id = pub_res.json().get("id")
    return {
        "success": True,
        "post_id": post_id,
        "is_reel": True,
        "video_url": video_url,
        "post_url": f"https://www.instagram.com/reel/{post_id}/" if post_id else None
    }

def wait_for_container(creation_id: str, access_token: str, max_wait: int = 40):
    """컨테이너 준비 상태 확인 대기"""
    endpoint = graph_endpoint(creation_id)
    start = time.time()
    while time.time() - start < max_wait:
        res = requests.get(
            endpoint,
            params={"fields": "status_code,status", "access_token": access_token},
            timeout=30
        )
        if res.status_code == 200:
            status = res.json().get("status_code")
            if status in ("FINISHED", "PUBLISHED"):
                return True
            if status == "ERROR":
                raise RuntimeError(f"Instagram 미디어 처리 오류: {res.text}")
        time.sleep(2)
    return True

def publish_to_instagram(
    image_paths: list = None,
    caption: str = "",
    account_id: str = None,
    access_token: str = None,
    folder: str = None,
    video_path: str = None
) -> dict:
    """
    인스타그램 사진/카드뉴스 캐러셀 게시물로 항상 발행 (슬라이드 1번 + 2번)
    """
    target_acc = account_id or DEFAULT_INSTAGRAM_ACCOUNT_ID
    target_tok = access_token or DEFAULT_META_ACCESS_TOKEN
    
    if not target_acc or not target_tok:
        raise RuntimeError("Instagram 계정 ID 또는 Meta 액세스 토큰이 없습니다.")
        
    if not image_paths:
        raise RuntimeError("발행할 이미지가 없습니다.")

    # 1. Cloudinary에 이미지들 업로드
    uploaded_urls = []
    for p in image_paths:
        url = upload_to_cloudinary(Path(p), folder)
        uploaded_urls.append(url)

    # 2. 인스타그램 미디어 컨테이너 생성
    if len(uploaded_urls) == 1:
        # 단일 이미지 발행
        create_url = graph_endpoint(f"{target_acc}/media")
        res = requests.post(
            create_url,
            data={"image_url": uploaded_urls[0], "caption": caption, "access_token": target_tok},
            timeout=60
        )
        if res.status_code >= 400:
            raise RuntimeError(f"미디어 생성 실패: {res.text}")
        container_id = res.json()["id"]
    else:
        # 캐러셀 (여러 장 슬라이드) 발행
        item_container_ids = []
        for img_url in uploaded_urls:
            item_url = graph_endpoint(f"{target_acc}/media")
            res = requests.post(
                item_url,
                data={
                    "image_url": img_url,
                    "is_carousel_item": "true",
                    "access_token": target_tok
                },
                timeout=60
            )
            if res.status_code >= 400:
                raise RuntimeError(f"슬라이드 아이템 생성 실패: {res.text}")
            item_container_ids.append(res.json()["id"])
            time.sleep(1)

        # 전체 캐러셀 묶음 컨테이너 생성
        carousel_url = graph_endpoint(f"{target_acc}/media")
        res = requests.post(
            carousel_url,
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(item_container_ids),
                "caption": caption,
                "access_token": target_tok
            },
            timeout=60
        )
        if res.status_code >= 400:
            raise RuntimeError(f"캐러셀 컨테이너 생성 실패: {res.text}")
        container_id = res.json()["id"]

    # 3. 컨테이너 준비 대기
    wait_for_container(container_id, target_tok)

    # 4. 최종 발행 (Publish)
    pub_url = graph_endpoint(f"{target_acc}/media_publish")
    pub_res = requests.post(
        pub_url,
        data={"creation_id": container_id, "access_token": target_tok},
        timeout=60
    )
    if pub_res.status_code >= 400:
        raise RuntimeError(f"최종 발행 실패: {pub_res.text}")
        
    post_id = pub_res.json().get("id")
    permalink = None
    if post_id:
        try:
            p_res = requests.get(
                f"https://graph.instagram.com/{post_id}?fields=permalink&access_token={target_tok}",
                timeout=10
            )
            if p_res.status_code == 200:
                permalink = p_res.json().get("permalink")
            if not permalink:
                f_res = requests.get(
                    graph_endpoint(f"{post_id}?fields=permalink&access_token={target_tok}"),
                    timeout=10
                )
                if f_res.status_code == 200:
                    permalink = f_res.json().get("permalink")
        except Exception:
            pass

    return {
        "success": True,
        "post_id": post_id,
        "media_count": len(uploaded_urls),
        "post_url": permalink or (f"https://www.instagram.com/p/{post_id}/" if post_id else None)
    }
