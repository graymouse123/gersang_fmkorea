import os
import re
import json
import time
import requests

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")
KEYWORDS = ["수용소", "말머리", "테스트"]  # 감시할 키워드 목록
SENT_FILE = "sent_posts.json"

def load_sent_posts():
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"기존 저장 파일 읽기 실패: {e}")
    return set()

def save_sent_posts(sent_ids):
    recent_ids = list(sent_ids)[-500:]
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(recent_ids, f, ensure_ascii=False, indent=2)

def check_board():
    if not WEBHOOK_URL:
        print("Webhook URL이 설정되지 않았습니다.")
        return

    if not SCRAPER_API_KEY:
        print("SCRAPER_API_KEY가 설정되지 않았습니다.")
        return

    sent_ids = load_sent_posts()
    new_sent_ids = set(sent_ids)

    # 1시간 주기 실행이므로 1페이지(최신글)만 스캔하여 API 커스텀 소모 축소
    target_url = "https://www.fmkorea.com/gersang?page=1"
    req_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={target_url}"

    try:
        res = requests.get(req_url, timeout=30)

        if res.status_code != 200:
            print(f"[1페이지] 응답 오류: Status {res.status_code}")
            return

        html = res.text

        # 게시글 링크 및 제목 추출
        pattern = r'<a[^>]*href=["\'](?:/|https://www\.fmkorea\.com/)?([0-9]{7,12})["\'][^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)

        unique_posts = []
        seen = set()

        for pid, rtitle in matches:
            clean_t = re.sub(r'<[^>]+>', '', rtitle).strip()
            clean_t = re.sub(r'\[[0-9]+\]$', '', clean_t).strip()
            
            if clean_t and len(clean_t) > 1 and not clean_t.isdigit():
                if pid not in seen and clean_t not in ["최신", "인기", "다음", "이전", "글쓰기"]:
                    seen.add(pid)
                    unique_posts.append((pid, clean_t))

        print(f"[1페이지] {len(unique_posts)}개 게시글 수신 완료")

        for post_id, title in unique_posts:
            if post_id in new_sent_ids:
                continue

            for kw in KEYWORDS:
                if kw in title:
                    print(f"[알림 전송] 키워드: {kw} | 제목: {title}")
                    if send_discord(post_id, title):
                        new_sent_ids.add(post_id)
                    break

    except Exception as e:
        print(f"스캔 중 오류 발생: {e}")

    save_sent_posts(new_sent_ids)

def send_discord(post_id, title):
    post_url = f"https://www.fmkorea.com/{post_id}"
    payload = {
        "embeds": [{
            "title": "🚨 감시 키워드 게시글 감지 (서버)",
            "description": f"**제목:** [{title}]({post_url})",
            "color": 15158332,
            "footer": {"text": "에펨코리아 거상 갤러리 깃허브 알리미"}
        }]
    }
    try:
        res = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        return res.status_code in [200, 204]
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")
        return False

if __name__ == "__main__":
    check_board()