import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import qrcode
from config import (
    BASE_DIR,
    LOCAL_IP,
    OUTPUT_DIR,
    SERVER_PORT,
    SERVER_URL,
    SOURCE_DIR,
    get_channels,
)
from core.auto_curator import auto_generate_curated_posts, process_local_uploaded_images
from core.queue_manager import (
    add_posts_to_queue,
    approve_and_publish_post,
    delete_post_item,
    load_queue,
    reject_post,
)
from core.vision_adapter import analyze_and_adapt_image
from core.image_transformer import transform_and_composite, create_cover_slide
from core.instagram_publisher import publish_to_instagram

app = FastAPI(title="InstaBonus Auto Web")

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
CAPTURES_DIR = BASE_DIR / "captures"
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
LOGO_DIR = BASE_DIR / "logos"
LOGO_DIR.mkdir(parents=True, exist_ok=True)

# QR 코드 자동 생성
qr_img = qrcode.make(SERVER_URL)
qr_img.save(str(STATIC_DIR / "qr.png"))


class AutoCurateRequest(BaseModel):
    count: int = 3
    category: str = "종합/인기"
    channel_id: Optional[str] = "default"
    lang: str = "ko"  # "ko", "ja", "en"
    logo_name: Optional[str] = None
    logo_text: Optional[str] = ""
    logo_position: str = "center"
    style_sample: Optional[str] = None


class ApproveRequest(BaseModel):
    post_id: str
    channel_id: str = "default"


class PostActionRequest(BaseModel):
    post_id: str


class UpdatePostRequest(BaseModel):
    post_id: str
    title: Optional[str] = None
    caption: Optional[str] = None


@app.get("/api/info")
def get_info():
    return {
        "local_ip": LOCAL_IP,
        "server_port": SERVER_PORT,
        "server_url": SERVER_URL,
        "channels": get_channels(),
    }


# ==========================================
# 🚀 100% 완전 자동 큐레이션 & 승인 대기열 API
# ==========================================
@app.post("/api/auto-curate")
def auto_curate(req: AutoCurateRequest):
    """
    AI가 알아서 최신 바이럴 소재를 발굴하고,
    [1번 썸네일 표지] + [2번 사연 카드] 2중 슬라이드로 완성하여 대기열에 등록합니다.
    """
    try:
        new_posts = auto_generate_curated_posts(
            count=req.count,
            category=req.category,
            channel_id=req.channel_id,
            lang=req.lang,
            logo_name=req.logo_name,
            logo_text=req.logo_text,
            logo_pos=req.logo_position,
            style_sample=req.style_sample
        )
        updated_queue = add_posts_to_queue(new_posts)
        return {
            "success": True,
            "created_count": len(new_posts),
            "queue": updated_queue
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/queue/clear")
def clear_queue_api():
    """대기열 비우기"""
    from core.queue_manager import save_queue
    save_queue([])
    return {"success": True, "queue": []}
@app.post("/api/upload-and-transform")
async def upload_and_transform(
    files: List[UploadFile] = File(...),
    channel_id: str = Form("default"),
    lang: str = Form("ko"),
    logo_text: str = Form("")
):
    """사용자가 직접 업로드한 로컬 사진들을 AI 분석하여 카드뉴스로 즉시 제작"""
    try:
        saved_paths = []
        for file in files:
            ext = Path(file.filename).suffix.lower() or ".jpg"
            save_name = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(saved_paths)}{ext}"
            save_path = CAPTURES_DIR / save_name
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(str(save_path))

        new_posts = process_local_uploaded_images(
            image_paths=saved_paths,
            channel_id=channel_id,
            lang=lang,
            logo_text=logo_text
        )
        updated_queue = add_posts_to_queue(new_posts)
        return {
            "success": True,
            "created_count": len(new_posts),
            "queue": updated_queue
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    """로고 이미지 업로드"""
    try:
        file_path = LOGO_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"success": True, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/queue")
def get_queue():
    """승인 대기열 목록 조회"""
    return {"success": True, "queue": load_queue()}


@app.post("/api/queue/approve")
def approve_post(req: ApproveRequest):
    """사용자가 승인 누르면 인스타그램 공식 API로 즉시 업로드"""
    try:
        pub_result = approve_and_publish_post(
            post_id=req.post_id,
            channel_id=req.channel_id
        )
        return {"success": True, "result": pub_result, "queue": load_queue()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"인스타 발행 실패: {str(e)}")


@app.post("/api/queue/reject")
def reject_post_api(req: PostActionRequest):
    """포스팅 반려/삭제"""
    updated_queue = delete_post_item(req.post_id)
    return {"success": True, "queue": updated_queue}


@app.post("/api/queue/delete")
def delete_post_api(req: PostActionRequest):
    """포스팅 완전 삭제 및 영구 제외 처리"""
    from core.auto_curator import record_deleted_story
    queue = load_queue()
    target = next((p for p in queue if p.get("id") == req.post_id), None)
    if target:
        if target.get("title"):
            record_deleted_story(target.get("title"))
        if target.get("raw_title"):
            record_deleted_story(target.get("raw_title"))
    updated_queue = delete_post_item(req.post_id)
    return {"success": True, "queue": updated_queue}


@app.post("/api/queue/update-post")
def update_post_api(req: UpdatePostRequest):
    """포스팅 제목/본문 수정 및 저장 (수정 모드 지원)"""
    queue = load_queue()
    for item in queue:
        if item.get("id") == req.post_id:
            if req.title is not None:
                item["title"] = req.title
            if req.caption is not None:
                item["caption"] = req.caption
            break
class AdjustStyleRequest(BaseModel):
    post_id: str
    offset_x: int = 0
    offset_y: int = 0
    font_size: int = 66
    font_weight: str = "Black"
    logo_position: str = "center"
    grad_opacity: int = 85
    grad_height: int = 50


@app.post("/api/card/adjust-style")
def adjust_style_api(req: AdjustStyleRequest):
    """[글자 스타일 및 위치 조정] 실시간 위치 이동 및 스타일 즉시 반영"""
    queue = load_queue()
    target_post = None
    for p in queue:
        if p.get("id") == req.post_id:
            target_post = p
            break
    if not target_post:
        raise HTTPException(status_code=404, detail="Post not found")

    raw_path_str = target_post.get("raw_image_path")
    out_img_url = target_post["image_url"].split("?")[0]
    out_path = BASE_DIR / out_img_url.lstrip("/")

    # 1. 원본 깨끗한 원본(raw) 이미지 자동 탐색 및 보장 (중복 자막 및 노이즈 중첩 방지)
    raw_path = None
    if raw_path_str and Path(raw_path_str).exists() and "final_" not in Path(raw_path_str).name:
        raw_path = Path(raw_path_str)
    else:
        filename = out_path.name
        m = re.search(r'final_(\d+)_', filename)
        if m:
            candidate = out_path.parent / f"raw_{m.group(1)}.jpg"
            if candidate.exists():
                raw_path = candidate
                target_post["raw_image_path"] = str(candidate)

    if not raw_path or not raw_path.exists():
        raw_path = out_path
        target_post["raw_image_path"] = str(raw_path)

    title = target_post.get("raw_title") or target_post.get("title", "")
    logo_text = target_post.get("logo_text", "")

    create_cover_slide(
        source_image_path=raw_path,
        output_path=out_path,
        title=title,
        logo_text=logo_text,
        logo_position=req.logo_position,
        font_size=req.font_size,
        font_weight=req.font_weight,
        offset_x=req.offset_x,
        offset_y=req.offset_y,
        grad_opacity=req.grad_opacity,
        grad_height=req.grad_height,
        target_aspect="1:1"
    )

    target_post["offset_x"] = req.offset_x
    target_post["offset_y"] = req.offset_y
    target_post["font_size"] = req.font_size
    target_post["font_weight"] = req.font_weight
    target_post["logo_position"] = req.logo_position
    target_post["grad_opacity"] = req.grad_opacity
    target_post["grad_height"] = req.grad_height

    cache_bust = f"{out_img_url}?t={int(time.time()*1000)}"
    target_post["image_url"] = cache_bust
    if target_post.get("slides"):
        target_post["slides"][0] = cache_bust

    from core.queue_manager import save_queue
    save_queue(queue)
    return {"success": True, "post": target_post, "queue": queue}


class RegenerateCardRequest(BaseModel):
    post_id: str


@app.post("/api/card/regenerate")
def regenerate_card_api(req: RegenerateCardRequest):
    """[재생성] 마음에 들지 않는 해당 카드를 새로운 실시간 기사(경기 결과 등)로 즉시 교체"""
    from core.auto_curator import auto_generate_curated_posts, record_deleted_story
    from core.queue_manager import save_queue

    queue = load_queue()
    target_idx = None
    target_post = None
    for idx, p in enumerate(queue):
        if p.get("id") == req.post_id:
            target_idx = idx
            target_post = p
            break
    if target_post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # 기존 기사는 영구 블랙리스트 처리하여 다시 나타나지 않도록 함
    if target_post.get("title"):
        record_deleted_story(target_post.get("title"))
    if target_post.get("raw_title"):
        record_deleted_story(target_post.get("raw_title"))

    channel_id = target_post.get("channel_id", "default")
    category = target_post.get("category", "스포츠 게시물")
    lang = target_post.get("lang", "ko")

    new_posts = auto_generate_curated_posts(
        count=1,
        category=category,
        channel_id=channel_id,
        lang=lang,
        logo_text=target_post.get("logo_text", ""),
        logo_pos=target_post.get("logo_position", "center")
    )

    if not new_posts:
        raise HTTPException(status_code=500, detail="새로운 실시간 기사를 가져오지 못했습니다.")

    new_post = new_posts[0]
    # 카드의 고유 ID는 유지하여 UI 상태 보존
    new_post["id"] = target_post["id"]
    queue[target_idx] = new_post
    save_queue(queue)

    return {"success": True, "post": new_post, "queue": queue}


@app.post("/api/card/replace-image")
async def replace_card_image_api(post_id: str = Form(...), file: UploadFile = File(...)):
    """[직접 넣기] 사용자가 선택한 사진으로 해당 카드의 배경 사진 교체"""
    queue = load_queue()
    target_post = None
    for p in queue:
        if p.get("id") == post_id:
            target_post = p
            break
    if not target_post:
        raise HTTPException(status_code=404, detail="Post not found")

    out_img_url = target_post["image_url"].split("?")[0]
    out_path = BASE_DIR / out_img_url.lstrip("/")

    raw_save = out_path.parent / f"custom_{int(time.time()*1000)}.jpg"
    with open(raw_save, "wb") as f:
        shutil.copyfileobj(file.file, f)

    target_post["raw_image_path"] = str(raw_save)
    title = target_post.get("raw_title") or target_post.get("title", "")

    create_cover_slide(
        source_image_path=raw_save,
        output_path=out_path,
        title=title,
        logo_text=target_post.get("logo_text", ""),
        logo_position=target_post.get("logo_position", "center"),
        font_size=target_post.get("font_size", 66),
        font_weight=target_post.get("font_weight", "Black"),
        offset_x=target_post.get("offset_x", 0),
        offset_y=target_post.get("offset_y", 0),
        grad_opacity=target_post.get("grad_opacity", 85),
        grad_height=target_post.get("grad_height", 50),
        target_aspect="1:1"
    )

    cache_bust = f"{out_img_url}?t={int(time.time()*1000)}"
    target_post["image_url"] = cache_bust
    if target_post.get("slides"):
        target_post["slides"][0] = cache_bust

    from core.queue_manager import save_queue
    save_queue(queue)
    return {"success": True, "post": target_post, "queue": queue}


@app.post("/api/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    """로고 이미지 업로드"""
    ext = Path(file.filename).suffix.lower() or ".png"
    save_name = f"logo_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    save_path = LOGO_DIR / save_name
    with open(save_path, "wb") as out_f:
        shutil.copyfileobj(file.file, out_f)
    return {"success": True, "filename": save_name, "url": f"/logos/{save_name}"}


@app.get("/api/download")
def download_file(file_path: str):
    """스마트폰 갤러리/다운로드 폴더 저장용 엔드포인트 (Content-Disposition: attachment)"""
    clean_path = file_path.lstrip("/").replace("\\", "/")
    target = BASE_DIR / clean_path
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    filename = target.name
    return FileResponse(
        str(target),
        media_type="image/jpeg",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# 정적 파일 마운트
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/captures", StaticFiles(directory=str(CAPTURES_DIR)), name="captures")
app.mount("/logos", StaticFiles(directory=str(LOGO_DIR)), name="logos")
app.mount("/source_images", StaticFiles(directory=str(SOURCE_DIR)), name="source_images")

@app.get("/")
def root():
    return FileResponse(str(STATIC_DIR / "index.html"))
