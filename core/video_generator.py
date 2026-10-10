import subprocess
import shutil
from pathlib import Path
from config import BASE_DIR

FFMPEG_BIN = shutil.which("ffmpeg") or r"C:\Users\PRO 10\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.EXE"

AUDIO_DIR = BASE_DIR / "audio"

CHANNEL_AUDIO = {
    "today_events": AUDIO_DIR / "breaking_news.mp3",
    "baseball": AUDIO_DIR / "sports_beat.mp3",
    "animals": AUDIO_DIR / "healing_pet.mp3",
    "celebrity": AUDIO_DIR / "celebrity_beat.mp3",
    "default": AUDIO_DIR / "breaking_news.mp3"
}

CHANNEL_AUDIO_NAMES = {
    "today_events": "🏛️ 시사/뉴스 브레이킹 비트",
    "baseball": "⚽ 스포츠 에너지 비트",
    "animals": "🐶 감성 힐링 어쿠스틱",
    "celebrity": "⭐ 트렌디 로파이 라운지",
    "default": "🎵 바이럴 트렌딩 사운드"
}

def get_audio_for_channel(channel_id: str) -> tuple[Path, str]:
    audio_path = CHANNEL_AUDIO.get(channel_id, CHANNEL_AUDIO["default"])
    if not audio_path.exists():
        # Fallback to any existing audio
        for candidate in AUDIO_DIR.glob("*.mp3"):
            return candidate, candidate.stem
    name = CHANNEL_AUDIO_NAMES.get(channel_id, "🎵 인스타 트렌딩 오디오")
    return audio_path, name

def create_reel_video(
    slide1_path: Path,
    slide2_path: Path,
    output_video_path: Path,
    channel_id: str = "default",
    duration_per_slide: float = 3.5
) -> tuple[Path, str]:
    """
    1번 표지 카드 + 2번 사연 요약 카드를 5~7초 릴스 비디오(MP4)로 변환하고
    채널별 감성/비트 배경음악(BGM)을 합성합니다.
    """
    audio_path, audio_name = get_audio_for_channel(channel_id)
    total_duration = duration_per_slide * 2.0
    fade_start = max(0.5, total_duration - 1.0)

    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    # ffmpeg 명령어로 1080x1080 고화질 릴스 MP4 인코딩
    cmd = [
        FFMPEG_BIN, "-y",
        "-loop", "1", "-t", str(duration_per_slide), "-i", str(slide1_path),
        "-loop", "1", "-t", str(duration_per_slide), "-i", str(slide2_path),
        "-ss", "0", "-t", str(total_duration), "-i", str(audio_path),
        "-filter_complex",
        f"[0:v]scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];"
        f"[1:v]scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];"
        f"[v0][v1]concat=n=2:v=1:a=0[v];"
        f"[2:a]afade=t=out:st={fade_start}:d=1.0,volume=0.35[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        str(output_video_path)
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg 릴스 영상 생성 실패: {res.stderr.decode('utf-8', errors='ignore')}")

    return output_video_path, audio_name
