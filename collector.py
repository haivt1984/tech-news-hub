import os
import re
import html
import time
import feedparser
import requests
from bs4 import BeautifulSoup
import sys

# Đảm bảo in log trực tiếp trên GitHub Actions console
sys.stdout.reconfigure(line_buffering=True)

# ================= CẤU HÌNH KẾT NỐI SUPABASE =================
RAW_SUPABASE = os.getenv("SUPABASE_URL", "https://lleeibzegmnycuingzgx.supabase.co")
match = re.search(r'https://[a-zA-Z0-9-]+\.supabase\.co', RAW_SUPABASE)
SUPABASE_URL = match.group(0) if match else "https://lleeibzegmnycuingzgx.supabase.co"

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE"
).strip("[]'\" \t\n\r")
# =============================================================

FEEDS = [
    # Tin tức công nghệ báo chí Việt Nam
    {"source": "VnExpress Số Hóa", "url": "https://vnexpress.net/rss/so-hoa.rss", "default_cat": "Thiết bị số"},
    {"source": "Tuổi Trẻ Công Nghệ", "url": "https://tuoitre.vn/rss/nhip-song-so.rss", "default_cat": "Trí tuệ nhân tạo (AI)"},
    {"source": "Thanh Niên Công Nghệ", "url": "https://thanhnien.vn/rss/cong-nghe.rss", "default_cat": "Xu hướng công nghệ"},
    {"source": "Dân Trí Sức Mạnh Số", "url": "https://dantri.com.vn/rss/suc-manh-so.rss", "default_cat": "Đời sống số"},
    {"source": "VietnamNet ICT", "url": "https://vietnamnet.vn/rss/thong-tin-truyen-thong.rss", "default_cat": "Chuyển đổi số"},

    # Kho cập nhật phần mềm, tiện ích & mã nguồn mở
    {"source": "MajorGeeks Tools", "url": "https://www.majorgeeks.com/files/rss", "default_cat": "Kho Phần Mềm & Tiện Ích"},
    {"source": "BetaNews Software", "url": "https://betanews.com/category/software/feed/", "default_cat": "Kho Phần Mềm & Tiện Ích"},
    {"source": "FOSSHub Open Source", "url": "https://www.fosshub.com/feed.xml", "default_cat": "Mã Nguồn Mở (FOSS)"}
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def clean_text(text):
    if not text:
        return ""
    text = html.unescape(text)
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

def scrape_full_article(url):
    """Cào trọn vẹn đoạn sapo mở đầu, toàn bộ nội dung văn bản và toàn bộ hình ảnh gốc từ trang báo"""
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        if res.status_code != 200:
            return None, None

        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # Dọn dẹp rác, bình luận, quảng cáo, mạng xã hội
        for junk in soup(['script', 'style', 'iframe', 'header', 'footer', 'nav', 'form', 'aside', 'noscript']):
            junk.decompose()
        for junk in soup.find_all(class_=re.compile(r'relate|box-tag|comment|banner|advert|social|author|breadcrumb|recommend|sticky|video-relate')):
            junk.decompose()

        container = None
        sapo_text = ""

        # 1. Định vị vùng nội dung theo từng cơ quan báo chí
        if "vnexpress.net" in url:
            container = soup.find(class_=re.compile(r'fck_detail'))
            sapo_tag = soup.find(class_=re.compile(r'description'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        elif "tuoitre.vn" in url:
            container = soup.find(id="main-detail-body") or soup.find(class_=re.compile(r'detail-content|content-detail'))
            sapo_tag = soup.find(class_=re.compile(r'detail-sapo|sapo'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        elif "thanhnien.vn" in url:
            container = soup.find(id="main-detail-body") or soup.find(class_=re.compile(r'detail-content|content-detail'))
            sapo_tag = soup.find(class_=re.compile(r'detail-sapo|sapo'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        elif "dantri.com.vn" in url:
            container = soup.find(class_=re.compile(r'singular-content|dt-news__content'))
            sapo_tag = soup.find(class_=re.compile(r'singular-sapo'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        elif "vietnamnet.vn" in url:
            container = soup.find(id="maincontent") or soup.find(class_=re.compile(r'content-detail|maincontent'))
            sapo_tag = soup.find(class_=re.compile(r'content-detail-sapo'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        # Dự phòng chung nếu là nguồn khác
        if not container:
            container = (
                soup.find('article') or 
                soup.find(class_=re.compile(r'fck_detail|detail-content|article-body|content-detail|entry-content')) or
                soup.find('div', id=re.compile(r'content|article|main')) or
                soup.body
            )

        content_html_parts = []
        lead_image = None
        added_images = set()

        # Thêm đoạn sapo mở đầu
        if sapo_text and len(sapo_text) > 15:
            content_html_parts.append(f'<p class="font-semibold text-slate-900 text-lg leading-relaxed mb-6 border-b border-slate-100 pb-4">{sapo_text}</p>')

        # 2. Quét tuần tự bóc tách ảnh và từng đoạn văn bản
        for element in container.find_all(['p', 'figure', 'div', 'h2', 'h3', 'img']):
            # Bóc tách ảnh từ thẻ <img>, <figure> hoặc thẻ <div> chứa ảnh
            if element.name in ['figure', 'img'] or (element.name == 'div' and ('photo' in str(element.get('class', [])).lower() or element.get('type') == 'Photo')):
                img_tag = element if element.name == 'img' else element.find('img')
                if img_tag:
                    # Bắt tất cả các cơ chế Lazy-load
                    src = (
                        img_tag.get('data-src') or 
                        img_tag.get('data-original') or 
                        img_tag.get('data-srcset') or 
                        img_tag.get('src') or ''
                    ).strip()

                    # Nếu có srcset, lấy URL đầu tiên
                    if ' ' in src and src.startswith('http'):
                        src = src.split(' ')[0]

                    if src.startswith('http') and src not in added_images and not any(ext in src.lower() for ext in ['icon', 'logo', 'svg', 'avatar', 'blank.gif', 'tracking']):
                        added_images.add(src)

                        caption_tag = element.find('figcaption') or element.find(class_=re.compile(r'caption|desc|text-caption'))
                        caption = clean_text(caption_tag.get_text()) if caption_tag else ""

                        if not lead_image:
                            lead_image = src

                        content_html_parts.append(f"""
                        <figure class="my-6">
                            <img src="{src}" alt="{caption}" class="w-full rounded-2xl border border-slate-200 shadow-sm object-cover max-h-[520px]" loading="lazy" onerror="this.style.display='none'">
                            {f'<figcaption class="text-xs text-center text-slate-500 mt-2 font-mono italic">{caption}</figcaption>' if caption else ''}
                        </figure>
                        """)

            # Bóc tách tiêu đề phụ giữa bài
            elif element.name in ['h2', 'h3']:
                text = clean_text(element.get_text())
                if 5 < len(text) < 150:
                    content_html_parts.append(f'<h3 class="text-xl font-bold text-slate-900 mt-8 mb-3 font-mono">{text}</h3>')

            # Bóc tách đoạn văn
            elif element.name == 'p':
                text = clean_text(element.get_text())
                if len(text) > 30 and not text.lower().startswith(('ảnh:', 'nguồn:', 'theo ')):
                    content_html_parts.append(f'<p class="mb-4 leading-relaxed text-slate-700 text-base sm:text-lg">{text}</p>')

        full_content = "\n".join(content_html_parts)
        return full_content, lead_image

    except Exception as e:
        print(f"      [!] Lỗi trích xuất nội dung: {e}")
        return None, None

def analyze_tech_article(title, desc, default_cat):
    title_clean = clean_text(title)
    desc_clean = clean_text(desc)
    content_lower = f"{title_clean} {desc_clean}".lower()

    category = default_cat
    if any(k in content_lower for k in ["download", "release", "portable", "installer", "cài đặt", "tiện ích", "update", "freeware"]):
        category = "Kho Phần Mềm & Tiện Ích"
    elif any(k in content_lower for k in ["open-source", "open source", "foss", "mã nguồn mở", "github", "linux"]):
        category = "Mã Nguồn Mở (FOSS)"
    elif any(k in content_lower for k in ["ai", "trí tuệ nhân tạo", "chatgpt", "openai", "copilot", "gemini", "robot", "llm"]):
        category = "Trí tuệ nhân tạo (AI)"
    elif any(k in content_lower for k in ["bảo mật", "hacker", "lừa đảo", "mã độc", "virus", "lỗ hổng", "tấn công mạng"]):
        category = "An ninh mạng & Bảo mật"
    elif any(k in content_lower for k in ["iphone", "samsung", "laptop", "chip", "máy tính", "bán dẫn", "card màn hình", "pc"]):
        category = "Phần cứng & Thiết bị"
    elif any(k in content_lower for k in ["phần mềm", "windows", "ios", "android", "ứng dụng"]):
        category = "Phần mềm & Nền tảng"

    summary = desc_clean if len(desc_clean) > 20 else title_clean
    insight = "Theo dõi kỹ các bản vá bảo mật và kiểm tra tính tương thích thiết bị trước khi cập nhật."

    if category == "Kho Phần Mềm & Tiện Ích":
        insight = "Kiểm tra kỹ mã hash hoặc quét file cài đặt qua VirusTotal trước khi chạy để đảm bảo an toàn tuyệt đối."
    elif category == "Mã Nguồn Mở (FOSS)":
        insight = "Ưu tiên các kho dự án có cộng đồng đóng góp sôi nổi và thường xuyên nhận bản cập nhật mới."
    elif category == "Trí tuệ nhân tạo (AI)":
        insight = "Tích hợp các công cụ AI vào quy trình làm việc thực tế để tự động hóa các tác vụ thủ công lặp lại."
    elif category == "An ninh mạng & Bảo mật":
        insight = "Bật xác thực đa yếu tố (MFA/2FA), tuyệt đối không mở các tệp đính kèm lạ và sao lưu dữ liệu quan trọng định kỳ."
    elif category == "Phần cứng & Thiết bị":
        insight = "Cân nhắc kỹ hiệu năng trên giá thành (P/P) và nhu cầu công việc thực tế trước khi đầu tư nâng cấp."

    return title_clean, summary, insight, category

print("=== BẮT ĐẦU CÀO TOÀN BỘ BÀI VIẾT, HÌNH ẢNH & KHO PHẦN MỀM ===")

for feed_info in FEEDS:
    source_name = feed_info["source"]
    print(f"\n[*] Đang quét: {source_name}")

    try:
        raw_xml = requests.get(feed_info["url"], headers=REQUEST_HEADERS, timeout=10).content
        parsed_feed = feedparser.parse(raw_xml)
    except Exception as e:
        print(f"    [x] Lỗi tải RSS {source_name}: {e}")
        continue

    entries = parsed_feed.entries[:ARTICLES_PER_FEED]
    print(f"    Tìm thấy {len(parsed_feed.entries)} bài. Xử lý {len(entries)} bài mới:")

    for entry in entries:
        original_title = entry.title
        original_url = entry.link
        description = entry.description if hasattr(entry, 'description') else entry.get('summary', '')

        if is_article_exists(original_url):
            print(f"    [-] Đã có trong cơ sở dữ liệu: {original_title[:40]}...")
            continue

        print(f"    -> Đang bóc tách toàn bộ: {original_title[:45]}...")

        title, summary, tips, category = analyze_tech_article(
            original_title, description, feed_info["default_cat"]
        )

        full_content, lead_image = scrape_full_article(original_url)

        if not full_content or len(full_content) < 80:
            full_content = f'<p class="mb-4 leading-relaxed text-slate-700 text-base sm:text-lg">{summary}</p>'

        record = {
            "title": title,
            "summary": summary,
            "tips": tips,
            "category": category,
            "content": full_content,
            "image_url": lead_image,
            "original_url": original_url
        }

        try:
            db_res = requests.post(SUPABASE_ENDPOINT, headers=SUPABASE_HEADERS, json=record, timeout=10)
            if db_res.status_code in [200, 201]:
                print(f"       ✔ Đã lưu thành công: [{category}] ({'Có ảnh gốc' if lead_image else 'Ảnh mặc định'})")
            else:
                print(f"       ✖ Lỗi Supabase: {db_res.status_code} - {db_res.text[:80]}")
        except Exception as e:
            print(f"       ✖ Lỗi kết nối: {e}")

        time.sleep(1.5)

print("\n=== HOÀN TẤT! CƠ SỞ DỮ LIỆU ĐÃ ĐƯỢC ĐỒNG BỘ ĐẦY ĐỦ ===")
