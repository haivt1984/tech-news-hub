import os
import re
import html
import time
import feedparser
import requests
import sys

sys.stdout.reconfigure(line_buffering=True)

# ================= CẤU HÌNH THÔNG TIN =================
# Lọc sạch triệt để mọi định dạng Markdown, ngoặc vuông, ngoặc tròn, xuống dòng \n
RAW_SUPABASE = os.getenv("SUPABASE_URL", "https://lleeibzegmnycuingzgx.supabase.co")
match = re.search(r'https://[a-zA-Z0-9-]+\.supabase\.co', RAW_SUPABASE)
if match:
    SUPABASE_URL = match.group(0)
else:
    SUPABASE_URL = "https://lleeibzegmnycuingzgx.supabase.co"

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE"
).strip("[]'\" \t\n\r")
# ======================================================

# Nguồn tin Công nghệ chuẩn hóa
FEEDS = [
    {"source": "VnExpress Số Hóa", "url": "https://vnexpress.net/rss/so-hoa.rss", "default_cat": "Thiết bị số"},
    {"source": "Tuổi Trẻ Công Nghệ", "url": "https://tuoitre.vn/rss/nhip-song-so.rss", "default_cat": "Trí tuệ nhân tạo"},
    {"source": "Thanh Niên Công Nghệ", "url": "https://thanhnien.vn/rss/cong-nghe.rss", "default_cat": "Xu hướng công nghệ"},
    {"source": "Dân Trí Sức Mạnh Số", "url": "https://dantri.com.vn/rss/suc-manh-so.rss", "default_cat": "Đời sống số"},
    {"source": "VietnamNet ICT", "url": "https://vietnamnet.vn/rss/thong-tin-truyen-thong.rss", "default_cat": "Chuyển đổi số"}
]

ARTICLES_PER_FEED = 50

SUPABASE_ENDPOINT = f"{SUPABASE_URL}/rest/v1/tech_articles"
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    clean = re.compile(r'<[^>]+>')
    text = re.sub(clean, '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_article_exists(url):
    try:
        check_url = f"{SUPABASE_ENDPOINT}?original_url=eq.{requests.utils.quote(url)}&select=id"
        res = requests.get(check_url, headers=SUPABASE_HEADERS, timeout=8)
        if res.status_code == 200 and len(res.json()) > 0:
            return True
    except Exception as e:
        print(f"      [!] Lỗi kiểm tra trùng lặp: {e}")
    return False

def analyze_tech_article(title, desc, default_cat):
    title_clean = clean_html(title)
    desc_clean = clean_html(desc)
    content_lower = f"{title_clean} {desc_clean}".lower()
    
    category = default_cat
    if any(k in content_lower for k in ["ai", "trí tuệ nhân tạo", "chatgpt", "openai", "copilot", "gemini", "robot"]):
        category = "Trí tuệ nhân tạo (AI)"
    elif any(k in content_lower for k in ["iphone", "samsung", "laptop", "chip", "máy tính", "điện thoại", "card màn hình"]):
        category = "Phần cứng & Thiết bị"
    elif any(k in content_lower for k in ["bảo mật", "hacker", "lừa đảo", "mã độc", "virus", "lỗ hổng"]):
        category = "An ninh mạng & Bảo mật"
    elif any(k in content_lower for k in ["phần mềm", "windows", "ios", "android", "ứng dụng", "cập nhật"]):
        category = "Phần mềm & Nền tảng"

    summary = desc_clean if len(desc_clean) > 20 else title_clean
    insight = "Theo dõi kỹ các bản vá bảo mật và kiểm tra tính tương thích thiết bị trước khi cập nhật."

    if "ai" in content_lower:
        insight = "Ứng dụng các công cụ AI vào quy trình làm việc để gia tăng năng suất và tự động hóa tác vụ lặp lại."
    elif "bảo mật" in content_lower or "lừa đảo" in content_lower:
        insight = "Bật xác thực hai yếu tố (2FA), không nhấp vào liên kết lạ và luôn sao lưu dữ liệu quan trọng."
    elif "phần cứng" in content_lower or "laptop" in content_lower or "chip" in content_lower:
        insight = "Cân nhắc hiệu năng trên giá thành (P/P) và nhu cầu thực tế trước khi nâng cấp thiết bị mới."

    return title_clean, summary, insight, category

print("=== BẮT ĐẦU CÀO TIN TỨC CÔNG NGHỆ CHUYÊN SÂU ===")

for feed_info in FEEDS:
    source_name = feed_info["source"]
    print(f"\n[*] Đang quét: {source_name}")

    try:
        raw_xml = requests.get(feed_info["url"], headers=REQUEST_HEADERS, timeout=10).content
        parsed_feed = feedparser.parse(raw_xml)
    except Exception as e:
        print(f"    [x] Lỗi nạp RSS {source_name}: {e}")
        continue

    entries = parsed_feed.entries[:ARTICLES_PER_FEED]
    print(f"    Tìm thấy {len(parsed_feed.entries)} bài. Xử lý {len(entries)} bài mới nhất:")

    for entry in entries:
        original_title = entry.title
        original_url = entry.link
        description = entry.description if hasattr(entry, 'description') else entry.get('summary', '')

        if is_article_exists(original_url):
            print(f"    [-] Đã có bài: {original_title[:40]}...")
            continue

        print(f"    -> Đang nạp: {original_title[:45]}...")

        title, summary, tips, category = analyze_tech_article(
            original_title, description, feed_info["default_cat"]
        )

        record = {
            "title": title,
            "summary": summary,
            "tips": tips,
            "category": category,
            "original_url": original_url
        }

        try:
            db_res = requests.post(SUPABASE_ENDPOINT, headers=SUPABASE_HEADERS, json=record, timeout=10)
            if db_res.status_code in [200, 201]:
                print(f"       ✔ Đã lưu thành công: [{category}]")
            else:
                print(f"       ✖ Lỗi Supabase: {db_res.status_code}")
        except Exception as e:
            print(f"       ✖ Lỗi lưu bài: {e}")

        time.sleep(1)

print("\n=== HOÀN TẤT! CƠ SỞ DỮ LIỆU CÔNG NGHỆ ĐÃ SẴN SÀNG ===")
