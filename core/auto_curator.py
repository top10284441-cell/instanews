import os
import json
import time
import html
import urllib.parse
from datetime import datetime
from pathlib import Path
import requests
import xml.etree.ElementTree as ET
from openai import OpenAI
from config import OPENAI_API_KEY, BASE_DIR, OUTPUT_DIR, LOGO_DIR
from core.image_transformer import create_cover_slide, create_story_slide, transform_and_composite

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

CHANNEL_FEEDS = {
    "animals": ["https://www.boredpanda.com/animals/feed/"],
    "baseball": [
        "https://www.chosun.com/arc/outboundfeeds/rss/category/sports/?outputType=xml"
    ],
    "today_events": ["https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=03&plink=RSSREADER"],  # 사회 일반
    "celebrity": [
        "https://www.chosun.com/arc/outboundfeeds/rss/category/entertainments/?outputType=xml",
        "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=14&plink=RSSREADER"
    ],
}

VIRAL_FEEDS = {
    "동물/힐링": ["https://www.boredpanda.com/animals/feed/"],
    "스포츠 게시물": [
        "https://www.chosun.com/arc/outboundfeeds/rss/category/sports/?outputType=xml"
    ],
    "사건으로 보는 오늘": ["https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=03&plink=RSSREADER"],
    "연예인 게시물": [
        "https://www.chosun.com/arc/outboundfeeds/rss/category/entertainments/?outputType=xml",
        "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=14&plink=RSSREADER"
    ],
    "감동/실화": ["https://www.boredpanda.com/good-news/feed/"],
    "세계이슈/미스터리": ["https://www.boredpanda.com/feed/"],
    "종합/인기": ["https://www.boredpanda.com/feed/"]
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

SEEN_FILE = BASE_DIR / "seen_stories.json"
DELETED_FILE = BASE_DIR / "deleted_stories.json"

def get_deleted_stories() -> set:
    if DELETED_FILE.exists():
        try:
            with open(DELETED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def record_deleted_story(title: str):
    if not title:
        return
    clean_t = title.strip().replace("\n", " ")
    deleted = get_deleted_stories()
    deleted.add(clean_t)
    try:
        with open(DELETED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(deleted), f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    save_seen_story(clean_t)

def get_seen_stories() -> set:
    seen = set()
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                seen = set(json.load(f))
        except Exception:
            seen = set()
    # 영구 삭제된 항목도 seen에 항상 병합
    seen.update(get_deleted_stories())
    return seen

def save_seen_story(title: str):
    seen = get_seen_stories()
    seen.add(title)
    if len(seen) > 300:
        seen = set(list(seen)[-300:])
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen), f, ensure_ascii=False)
    except Exception:
        pass

def fetch_real_viral_stories(category: str = "종합/인기", channel_id: str = "default", limit: int = 5, ignore_seen: bool = False) -> list:
    """해외/국내 최신 화제의 뉴스 및 스토리 수집 (중복 배제 및 매번 무작위 탐색)"""
    import random
    import re

    # 채널 ID 우선 매핑, 없으면 카테고리 매핑
    feed_urls = []
    if channel_id and channel_id in CHANNEL_FEEDS:
        val = CHANNEL_FEEDS[channel_id]
        feed_urls = val if isinstance(val, list) else [val]
    elif category in VIRAL_FEEDS:
        val = VIRAL_FEEDS[category]
        feed_urls = val if isinstance(val, list) else [val]
    else:
        feed_urls = ["https://www.boredpanda.com/feed/"]

    stories = []
    seen = get_seen_stories()
    deleted_stories = get_deleted_stories()

    is_baseball_mode = (channel_id == "baseball" or category == "스포츠 게시물")
    is_celebrity_mode = (channel_id == "celebrity" or category == "연예인 게시물")

    # 🚨 인스타그램 추천 차단 방지: 정치/군사/정당/무기 키워드 엄격 배제
    POLITICAL_BLACKLIST = [
        "대통령", "윤석열", "이재명", "국민의힘", "민주당", "국회", "의원", "정치", "선거", "정당",
        "북한", "미사일", "군사", "무기", "국방", "지뢰", "남북", "핵", "사격", "포로",
        "5·18", "특검", "청문회", "탄핵", "공천", "당대표", "여당", "야당"
    ]

    # ⚾ 한국 야구 전용 엄격 필터: 타 종목 및 순수 미국 MLB 전면 배제
    EXCLUDE_ALL_NON_BASEBALL = [
        "씨름", "태백장사", "금강장사", "천하장사", "장사씨름", "골프", "KLPGA", "PGA", "LPGA",
        "축구", "K리그", "손흥민", "이강인", "김민재", "호날두", "메시", "프리미어리그", "챔피언스리그",
        "농구", "KBL", "NBA", "배구", "V리그", "수영", "피겨", "스케이팅", "쇼트트랙", "탁구", "배드민턴", "테니스", "당구",
        "UFC", "FIFA", "레슬러", "레슬링", "핸드볼", "양궁", "사격", "펜싱", "마라톤", "육상",
        "DB", "원주DB", "세이커스", "SK나이츠", "현대모비스", "가스공사"
    ]
    MLB_EXCLUDE = [
        "ML", "MLB", "메이저리그", "NLCS", "ALCS", "ALDS", "NLDS", "월드시리즈",
        "다저스", "양키스", "오타니", "샌디에이고", "애틀랜타", "밀워키", "필라델피아",
        "클리블랜드", "보스턴", "토론토", "메츠", "휴스턴", "디트로이트",
        "김하성", "이정후", "배지환", "美 ", "美,", "빅리그"
    ]
    KBO_TEAMS = [
        "LG", "트윈스", "롯데", "자이언츠", "KIA", "기아", "타이거즈", "한화", "이글스",
        "삼성", "라이온즈", "두산", "베어스", "KT", "위즈", "SSG", "랜더스", "NC", "다이노스", "키움", "히어로즈"
    ]
    KBO_KEYWORDS = [
        "KBO", "프로야구", "한국시리즈", "포스트시즌", "플레이오프", "와일드카드",
        "홈런", "안타", "타자", "투수", "선발", "완봉", "세이브", "타율", "타점", "평자", "가을야구"
    ]

    # ⭐ 한국 연예인 전용 엄격 필터: 해외/할리우드 가십 배제
    FOREIGN_CELEB_EXCLUDE = ["할리우드", "외신", "양자경", "디즈니", "팝스타", "해외", "빌보드", "마블", "칸"]

    raw_candidates = []

    for feed_url in feed_urls:
        try:
            res = requests.get(feed_url, headers=HEADERS, timeout=12)
            if res.status_code != 200:
                continue
            root = ET.fromstring(res.content)
            channel_node = root.find("channel")
            items = channel_node.findall("item") if channel_node is not None else root.findall(".//item")

            for it in items:
                title = it.find("title").text if it.find("title") is not None else ""
                title = title.strip()
                link = it.find("link").text.strip() if it.find("link") is not None else ""
                if not title:
                    continue

                # 사용자가 삭제한 기사는 100% 영구 차단
                if title in deleted_stories or any(d in title for d in deleted_stories if len(d) >= 3):
                    continue

                if not ignore_seen and (title in seen):
                    continue

                if any(bad in title for bad in POLITICAL_BLACKLIST):
                    continue

                desc = it.find("description").text if it.find("description") is not None else ""
                clean_desc = re.sub(r'<[^>]+>', ' ', desc).strip() if desc else ""
                if any(bad in clean_desc for bad in POLITICAL_BLACKLIST):
                    continue

                # 이미지 찾기 (content, enclosure, thumbnail, desc img 태그)
                img_url = None
                media = it.find("{http://search.yahoo.com/mrss/}content") or it.find("{http://search.yahoo.com/mrss/}thumbnail")
                if media is not None and media.attrib.get("url"):
                    img_url = media.attrib.get("url")
                if not img_url:
                    enc = it.find("enclosure")
                    if enc is not None and enc.attrib.get("url"):
                        img_url = enc.attrib.get("url")
                if not img_url and desc:
                    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc)
                    if m:
                        img_url = m.group(1)

                # ⚾ 한국 야구 모드일 때 엄격 검증
                if is_baseball_mode:
                    if any(ex in title for ex in EXCLUDE_ALL_NON_BASEBALL):
                        continue
                    if any(mlb in title for mlb in MLB_EXCLUDE):
                        continue
                    if title.startswith("[포토]") or title.startswith("[사진]"):
                        continue
                    # 드래프트, 신인 계약, 엔트리 등 비경기 이슈 전면 배제 (오직 실제 경기 중심)
                    EXCLUDE_NON_MATCH_TOPICS = [
                        "드래프트", "신인 선수", "계약 완료", "계약금", "라밤바", "등록", "말소", "1군 등록",
                        "입단", "FA", "스카우트", "시구", "이벤트", "만원관중", "출정식", "돔구장", "규제"
                    ]
                    if any(no in title for no in EXCLUDE_NON_MATCH_TOPICS):
                        continue

                    # 반드시 한국 프로야구(KBO 10개 구단 또는 KBO 키워드) 관련이어야 함
                    is_kbo = ("/baseball/" in link) or any(team in title for team in KBO_TEAMS) or any(kw in title for kw in KBO_KEYWORDS)
                    if not is_kbo:
                        continue
                    # 이미지 URL이 없더라도 링크를 보존하여 선별 시 og:image 추출 가능하도록 저장
                    raw_candidates.append((title, img_url, clean_desc, link))

                # ⭐ 한국 연예인 모드일 때 엄격 검증
                elif is_celebrity_mode:
                    if not img_url:
                        continue
                    if any(fx in title for fx in FOREIGN_CELEB_EXCLUDE):
                        continue
                    if title.startswith("[포토]") or title.startswith("[사진]"):
                        continue
                    raw_candidates.append((title, img_url, clean_desc, link))

                else:
                    if not img_url:
                        continue
                    raw_candidates.append((title, img_url, clean_desc, link))
        except Exception as e:
            print("Error fetching feed:", feed_url, e)

    # ⚾ 한국 야구의 경우 경기 결과(승패, 스코어, 역전, 리뷰) 중심 + [구단 다변화] (동일 구단 중복 배제)
    if is_baseball_mode:
        def get_baseball_result_score(cand):
            t = cand[0]
            sc = 0
            if any(rev in t for rev in ["[리뷰]", "리뷰]", "[게임노트]"]):
                sc += 25
            if re.search(r'\d+-\d+', t) or "점차" in t or "점 차" in t:
                sc += 20
            if any(w in t for w in ["승리", "제압", "이겼다", "완승", "격파", "꺾었다", "침몰", "패배"]):
                sc += 15
            if any(w in t for w in ["역전", "끝내기", "결정타", "쐐기포", "스리런", "만루홈런", "포효", "승투", "승리투수", "완봉", "고춧가루"]):
                sc += 12
            if any(w in t for w in ["확정", "탈환", "수성", "연승", "연패 탈출"]):
                sc += 8
            if any(w in t for w in ["가을야구", "KS", "PO", "경계", "준비"]):
                sc += 6
            # 기아, 삼성, 두산 등 주요 인기 구단 가산점 부여 (다양성 확보)
            if any(fav in t for fav in ["KIA", "기아", "삼성", "두산", "SSG"]):
                sc += 5
            return sc

        def get_primary_team(title):
            # 실제 경기 승리팀 및 주요 화제 구단 판별
            if any(k in title for k in ["NC 7-2", "네일", "KIA 이겼다", "KIA 승리", "최원준", "이범호", "황동하", "타이거즈"]):
                return "KIA"
            if any(k in title for k in ["SSG", "랜더스", "피날레 승리", "최지훈", "박성한"]):
                return "SSG"
            if any(k in title for k in ["두산", "베어스", "곽빈", "김태형"]):
                return "두산"
            if any(k in title for k in ["삼성", "라이온즈", "원태인", "구자욱", "강민호", "박진만", "페덱"]):
                return "삼성"
            if any(k in title for k in ["한화", "이글스", "류현진", "문동주", "노시환", "김경문"]):
                return "한화"
            if any(k in title for k in ["KT", "위즈", "강백호", "고영표", "이강철"]):
                return "KT"
            if any(k in title for k in ["NC", "다이노스", "구창모", "손아섭", "박민우"]):
                return "NC"
            if any(k in title for k in ["키움", "히어로즈", "송성문"]):
                return "키움"
            if any(k in title for k in ["롯데", "자이언츠", "레이예스", "전준우", "황성빈", "김민성", "전민재"]):
                return "롯데"
            if any(k in title for k in ["LG", "트윈스", "염경엽", "오지환", "박해민", "문보경"]):
                return "LG"
            for tm in ["KIA", "삼성", "두산", "한화", "롯데", "SSG", "NC", "KT", "키움", "LG"]:
                if tm in title:
                    return tm
            return "기타"

        def fetch_og_image(article_url):
            try:
                r = requests.get(article_url, headers=HEADERS, timeout=4)
                if r.status_code == 200:
                    m = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', r.text)
                    if not m:
                        m = re.search(r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']', r.text)
                    if m:
                        return html.unescape(m.group(1))
            except Exception:
                pass
            return None

        # 점수 순으로 정렬하되 동점 시 무작위 셔플
        random.shuffle(raw_candidates)
        raw_candidates.sort(key=get_baseball_result_score, reverse=True)

        selected_primary_teams = set()
        chosen = []

        # 1차: 각 카드마다 서로 다른 대표 구단(KIA, 삼성, 두산, SSG 등) 무조건 1개씩 선발
        for cand in raw_candidates:
            t, img_url, clean_desc, cand_link = cand
            p_team = get_primary_team(t)
            
            # 이미 선택된 구단과 겹치면 절대 선발하지 않음! (LG 독점 및 특정 구단 편중 차단)
            if p_team != "기타" and p_team in selected_primary_teams:
                continue

            # 이미지 확보 (없으면 기사 페이지에서 고화질 og:image 즉시 추출)
            if not img_url and cand_link:
                img_url = fetch_og_image(cand_link)
            if not img_url:
                continue

            if p_team != "기타":
                selected_primary_teams.add(p_team)
            chosen.append((t, img_url, clean_desc))
            if len(chosen) >= limit:
                break

        # 2차: 서로 다른 구단으로 limit를 다 못 채운 경우 나머지 후보 기사에서 보충
        if len(chosen) < limit:
            for cand in raw_candidates:
                t, img_url, clean_desc, cand_link = cand
                if any(c[0] == t for c in chosen):
                    continue
                if not img_url and cand_link:
                    img_url = fetch_og_image(cand_link)
                if not img_url:
                    continue
                chosen.append((t, img_url, clean_desc))
                if len(chosen) >= limit:
                    break

        for title, img_url, clean_desc in chosen:
            save_seen_story(title)
            stories.append({
                "original_title": title,
                "image_url": img_url,
                "description": clean_desc[:300]
            })
            if len(stories) >= limit:
                break
    else:
        random.shuffle(raw_candidates)
        for cand in raw_candidates:
            title, img_url, clean_desc = cand[0], cand[1], cand[2]
            if not img_url:
                continue
            save_seen_story(title)
            stories.append({
                "original_title": title,
                "image_url": img_url,
                "description": clean_desc[:300]
            })
            if len(stories) >= limit:
                break

    return stories

def auto_generate_curated_posts(
    count: int = 3,
    category: str = "종합/인기",
    channel_id: str = "default",
    lang: str = "ko",
    logo_name: str = None,
    logo_text: str = "",
    logo_pos: str = "center",
    style_sample: str = None
) -> list:
    """
    1. 실제로 조회수가 폭발한 해외/국내 화제의 실사 사진과 스토리를 수집
    2. GPT-4o로 한국어/일본어/영어 후킹 제목, 2번 슬라이드 요약, 본문 캡션 기획
    3. [1번 표지 슬라이드] + [2번 사연 카드 슬라이드] 2중 캐러셀 렌더링
    """
    if not client:
        raise RuntimeError("OpenAI API 키가 필요합니다.")

    viral_items = fetch_real_viral_stories(category=category, channel_id=channel_id, limit=count)
    if len(viral_items) < count:
        # 채널 전용인 경우 일반 바이럴(동물/유머)로 왜곡되지 않도록 같은 피드에서 seen을 무시하고 신선한 기사 재검색 (삭제된 기사는 여전히 차단)
        if channel_id in ("baseball", "celebrity") or category in ("스포츠 게시물", "연예인 게시물"):
            viral_items = fetch_real_viral_stories(category=category, channel_id=channel_id, limit=count, ignore_seen=True)
        else:
            viral_items = fetch_real_viral_stories(category="종합/인기", channel_id="default", limit=count)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    curated_dir = OUTPUT_DIR / f"viral_{timestamp}_{lang}"
    curated_dir.mkdir(parents=True, exist_ok=True)

    logo_path = None
    if logo_name:
        c_logo = LOGO_DIR / logo_name
        if c_logo.exists():
            logo_path = str(c_logo)

    lang_instructions = {
        "ko": "한국어로 작성하세요. 인스타에서 100만 조회가 터질 수 있는 강력한 호기심 유발 매거진 문체.",
        "ja": "日本語で作成してください。日本のインスタバイラル文体（ます調、絵文字）および現地の人気ハッシュタグ。",
        "en": "Write in viral English carousel/post style with catchy headlines and trending hashtags."
    }

    style_instruction = f"\n[사용자 지정 스타일 양식 참고]:\n{style_sample}\n위 샘플 양식의 톤앤매너와 문체를 완벽히 학습하여 작성하세요.\n" if style_sample else ""

    results = []
    for idx, story in enumerate(viral_items[:count]):
        raw_img_path = curated_dir / f"raw_{idx+1:02d}.jpg"
        slide1_path = curated_dir / f"final_{idx+1:02d}_slide1.jpg"
        slide2_path = curated_dir / f"final_{idx+1:02d}_slide2.jpg"

        # 1. 실제 고화질 원본 사진 다운로드
        try:
            target_img_url = html.unescape(story["image_url"])
            img_res = requests.get(target_img_url, headers=HEADERS, timeout=15)
            if img_res.status_code == 200:
                with open(raw_img_path, "wb") as f:
                    f.write(img_res.content)
            else:
                print(f"Failed to download image (status {img_res.status_code}): {target_img_url}")
                continue
        except Exception as e:
            print(f"Failed to download image {story['image_url']}:", e)
            continue

        # 채널별 맞춤 AI 디렉팅 지침
        channel_special_rule = ""
        if channel_id == "baseball" or category == "스포츠 게시물":
            channel_special_rule = """
[스포츠/야구 채널 전용 수칙 - 100% 경기 결과 중심 & 구단 공정 다변화]:
- 반드시 대한민국 한국 프로야구(KBO 리그)의 **실제 경기 결과(승패, 스코어, 역전승, 결정타, 수훈 선수 활약, 결정적 승부처)** 중심으로 작성하세요!
- 특정 구단(LG 등)으로 편향되지 말고, 기사 원문과 사진에 등장하는 실제 주인공 구단(예: KIA 타이거즈, SSG 랜더스, 삼성 라이온즈, 두산 베어스 등)을 뚜렷한 주인공으로 작성하세요!
- 기사 제목에 여러 구단이 복합 언급된 경우(예: "LG 지고 KIA 이겼다! NC 7-2 제압"), 패배팀이 아니라 실제로 7-2 대승을 거둔 승리 구단(KIA 타이거즈)과 수훈 선수를 중심 주인공으로 표지 제목(hooking_title)과 캡션을 작성해야 합니다!
- 표지 제목 1줄은 경기 결과 핵심(승리 팀명 및 스코어/대승/역전), 2줄은 결정적 순간 또는 수훈 선수를 강조하세요. (예: "KIA, NC 7-2 완파 승리!\\n네일 13승 달성 대포효!")
"""
        elif channel_id == "celebrity" or category == "연예인 게시물":
            channel_special_rule = """
[연예/스타 채널 전용 수칙]:
- 반드시 대한민국 한국 연예인(인기 배우, K-POP 아이돌, 대세 예능인, 한국 드라마/예능 스타) 중심의 화제 스토리로 기획하세요.
- 외국의 할리우드 스타는 배제하고, 국내 팬들이 즉각 반응하고 댓글이 폭발할 수 있는 한국 스타들의 이야기로 호기심을 극대화하세요.
"""

        # 2. GPT-4o Vision 기반 기획 (사진 속 실제 인물/구단/장면과 100% 일치하도록 검증)
        prompt = f"""
다음은 실제 화제의 뉴스 및 스토리입니다:
원문 제목: "{story['original_title']}"
원문 내용 요약: "{story['description']}"

인스타그램 카드뉴스(1번 표지 슬라이드 + 2번 사연 요약 슬라이드)를 기획해 주세요.
타겟 언어: {lang} ({lang_instructions.get(lang, '한국어')})
{style_instruction}
{channel_special_rule}

 작성 규칙:
0. [인스타그램 알고리즘 필수 수칙]: 정치인, 정당, 선거, 군사/무기/전쟁 관련 내용은 인스타그램 탐색 추천에서 차단되므로 절대 다루지 마세요. 일상, 스포츠 경기 결과, 감동 실화, 화제의 사건 등 대중적인 이야기로 각색하세요.
★ [사진 속 인물/구단 100% 일치 수칙]:
함께 첨부된 실제 사진을 면밀히 확인하세요! 기사 텍스트에 여러 선수나 화제가 복합적으로 언급되어 있더라도, **반드시 첨부된 사진에 실제로 찍혀 있는 인물(얼굴, 유니폼, 구단 로고)을 주인공으로 하여 표지 제목(hooking_title)과 캡션을 작성**해야 합니다. (사진에 나오는 인물과 제목의 주인공이 불일치하는 것을 엄격히 방지하세요!)
1. hooking_title: 표지용 2줄 제목 (반드시 \\n 줄바꿈 포함). 
   - 1줄: 사진 속 인물/팀의 상황 제시
   - 2줄: 충격 또는 감동 포인트 (경기 결과/명장면)
2. story_points: 2번 슬라이드에 들어갈 핵심 사연/결과 요약 불렛포인트 4개 (각 줄 20~30자 내외).
3. caption: **[초고품질 매거진 심층 본문 - 필수 분량 500자~800자 이상]**
   - 2~3줄의 단순 요약은 절대 금지합니다! 인스타그램 이용자가 끝까지 읽고 몰입할 수 있도록 3~4개의 탄탄한 단락으로 상세하게 서술하세요.
   - 단락 1 [도입부]: 스크롤을 멈추게 만드는 강렬한 상황 브리핑과 핵심 이슈 제기
   - 단락 2 [상세 전개]: 사건/경기의 전후 배경, 구체적인 사실관계와 전개 과정, 당사자들의 입장 및 수치/기록 등 디테일한 내막
   - 단락 3 [결과 및 영향]: 판결 결과, 경기 승패의 여파, 전문가/대중의 반응, 사회적/리그 내 시사점
   - 단락 4 [독자 소통]: 댓글 참여율(Engagement)을 폭발시킬 수 있는 흥미진진한 질문 문구
   - 문체: 어색한 외래어(예: shocking 등) 남용을 금지하고, 세련되고 몰입감 넘치는 전문 에디터 문체로 작성하세요. 적절한 이모지를 문맥에 맞게 활용하세요.
4. hashtags: 관련 바이럴 해시태그 5개.

반드시 아래 JSON 형식으로 응답하세요:
{{
  "hooking_title": "1줄 제목\\n2줄 제목",
  "story_points": [
    "포인트 1",
    "포인트 2",
    "포인트 3",
    "포인트 4"
  ],
  "caption": "인스타 본문에 들어갈 500~800자 분량의 풍부하고 깊이 있는 상세 매거진 스토리 (3~4개 단락)...",
  "hashtags": ["#태그1", "#태그2", "#태그3", "#태그4", "#태그5"]
}}
"""

        try:
            # 사진을 base64로 인코딩하여 GPT Vision에 전달 (사진 속 인물과 제목 불일치 방지)
            import base64
            with open(raw_img_path, "rb") as img_f:
                b64_data = base64.b64encode(img_f.read()).decode("utf-8")

            res_ai = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_data}",
                                "detail": "low"
                            }
                        }
                    ]
                }],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            ai_data = json.loads(res_ai.choices[0].message.content)
            title = ai_data.get("hooking_title", story["original_title"])
            points = ai_data.get("story_points", [story["original_title"]])
            caption = ai_data.get("caption", "")
            raw_tags = ai_data.get("hashtags", [])
            tags = " ".join([t if t.startswith("#") else f"#{t}" for t in raw_tags]) if raw_tags else ""
            cta = "\n\n💡 나중에 다시 보시려면 오른쪽 아래 [저장(북마크)]을 눌러두세요!\n📢 친구/지인에게 공유하고 함께 소식을 나눠보세요!"
            disclaimer = f"{cta}\n\n📌 출처: 뉴스 보도 및 공개 자료 인용\n📩 저작권 관련 문의는 DM 주시면 즉시 삭제 처리해 드립니다."
            full_caption = f"{caption}{disclaimer}\n\n.\n.\n{tags}" if tags else f"{caption}{disclaimer}"

            # 3. [1번 표지 슬라이드] 렌더링 (영상과 동일한 풀이미지 + 하단 다크 그라데이션)
            create_cover_slide(
                source_image_path=raw_img_path,
                output_path=slide1_path,
                title=title,
                logo_text=logo_text,
                logo_path=logo_path,
                logo_position=logo_pos,
                font_size=66,
                target_aspect="1:1"
            )

            post_id = f"post_{timestamp}_{idx+1:02d}"
            slide1_url = f"/output/viral_{timestamp}_{lang}/final_{idx+1:02d}_slide1.jpg"

            results.append({
                "id": post_id,
                "category": category,
                "channel_id": channel_id,
                "title": title.replace("\n", " "),
                "caption": full_caption,
                "image_url": slide1_url,
                "slides": [slide1_url],
                "raw_image_path": str(raw_img_path),
                "raw_title": title,
                "font_size": 66,
                "font_weight": "Black",
                "offset_x": 0,
                "offset_y": 0,
                "logo_position": logo_pos,
                "lang": lang,
                "status": "pending",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            })

        except Exception as e:
            print("AI curation generation error:", e)

    return results


def process_local_uploaded_images(
    image_paths: list,
    channel_id: str = "default",
    lang: str = "ko",
    logo_text: str = ""
) -> list:
    """
    사용자가 업로드한 로컬 사진을 분석하여 [1번 표지] + [2번 요약 카드] 생성 후 반환
    """
    import base64
    if not client:
        raise RuntimeError("OpenAI API 키가 필요합니다.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir = OUTPUT_DIR / f"upload_{timestamp}_{lang}"
    upload_dir.mkdir(parents=True, exist_ok=True)

    category_map = {
        "animals": "동물 게시물",
        "baseball": "스포츠 게시물",
        "today_events": "사건으로 보는 오늘",
        "celebrity": "연예인 게시물",
        "default": "인스타 카드"
    }
    category_name = category_map.get(channel_id, "인스타 카드")

    results = []
    for idx, img_path in enumerate(image_paths):
        p = Path(img_path)
        if not p.exists():
            continue

        slide1_path = upload_dir / f"final_{idx+1:02d}_slide1.jpg"
        slide2_path = upload_dir / f"final_{idx+1:02d}_slide2.jpg"

        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        ext = p.suffix.lower().replace(".", "")
        mime = "image/png" if ext == "png" else "image/jpeg"

        prompt = f"""
이 이미지를 보고 인스타그램 1:1 카드뉴스(1번 표지 슬라이드 + 2번 사연 요약 슬라이드)를 기획해 주세요.
카테고리: {category_name}
언어: {lang}

작성 규칙:
1. hooking_title: 표지용 2줄 헤드라인 (반드시 줄바꿈 \\n 포함). 1줄은 상황 제시, 2줄은 충격/감동/핵심 포인트.
2. story_points: 2번 슬라이드에 들어갈 핵심 요약 불렛포인트 4개 (각 줄 20~30자 내외).
3. caption: 인스타 본문 전체 스토리 (이모지 포함).
4. hashtags: 관련 해시태그 5개.

반드시 아래 JSON 형식으로 응답하세요:
{{
  "hooking_title": "1줄 제목\\n2줄 부제목",
  "story_points": ["포인트 1", "포인트 2", "포인트 3", "포인트 4"],
  "caption": "본문...",
  "hashtags": ["#태그1", "#태그2"]
}}
"""

        try:
            res_ai = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                    ]
                }],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            ai_data = json.loads(res_ai.choices[0].message.content)
            title = ai_data.get("hooking_title", "화제의 순간\n인스타그램 스토리")
            points = ai_data.get("story_points", ["사연 요약 1", "사연 요약 2", "사연 요약 3", "사연 요약 4"])
            caption = ai_data.get("caption", "")
            tags = " ".join(ai_data.get("hashtags", []))
            disclaimer = "\n\n📌 출처: 커뮤니티 및 공개 자료 인용\n📩 저작권 관련 문의는 DM 주시면 즉시 삭제 처리해 드립니다."
            full_caption = f"{caption}{disclaimer}\n\n.\n.\n{tags}" if tags else f"{caption}{disclaimer}"

            # 1번 슬라이드 (표지)
            create_cover_slide(
                source_image_path=p,
                output_path=slide1_path,
                title=title,
                logo_text=logo_text,
                target_aspect="1:1"
            )

            post_id = f"post_upload_{timestamp}_{idx+1:02d}"
            slide1_url = f"/output/upload_{timestamp}_{lang}/final_{idx+1:02d}_slide1.jpg"

            results.append({
                "id": post_id,
                "category": category_name,
                "channel_id": channel_id,
                "title": title.replace("\n", " "),
                "caption": full_caption,
                "image_url": slide1_url,
                "slides": [slide1_url],
                "raw_image_path": str(p),
                "raw_title": title,
                "font_size": 66,
                "font_weight": "Black",
                "offset_x": 0,
                "offset_y": 0,
                "logo_position": "center",
                "lang": lang,
                "status": "pending",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        except Exception as e:
            print(f"Error processing uploaded image {p}:", e)

    return results

