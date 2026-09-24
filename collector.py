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

# Danh sách nguồn cấp RSS báo chí công nghệ chính thống Việt Nam
FEEDS = [
    {"source": "VnExpress Số Hóa", "url": "https://vnexpress.net/rss/so-hoa.rss", "default_cat": "Thiết bị số"},
    {"source": "Tuổi Trẻ Công Nghệ", "url": "https://tuoitre.vn/rss/nhip-song-so.rss", "default_cat": "Trí tuệ nhân tạo (AI)"},
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
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
    """Cào trọn vẹn toàn bộ bài viết, các bước hướng dẫn, code box và hình ảnh gốc"""
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        if res.status_code != 200:
            return None, None

        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # Dọn dẹp rác, quảng cáo, widget mua sắm, bình luận
        for junk in soup(['script', 'style', 'iframe', 'header', 'footer', 'nav', 'form', 'aside', 'noscript']):
            junk.decompose()
        for junk in soup.find_all(class_=re.compile(r'relate|box-tag|comment|banner|advert|social|author|breadcrumb|recommend|sticky|video-relate|box-buy|price-box|affiliate')):
            junk.decompose()

        container = None
        sapo_text = ""

        # 1. Xử lý chuyên sâu cho Quantrimang.com
        if "quantrimang.com" in url:
            container = soup.find(id="main-detail-body") or soup.find(class_=re.compile(r'detail-content|content-detail|article-body'))
            sapo_tag = soup.find(class_=re.compile(r'detail-sapo|sapo|lead'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        # 2. VnExpress
        elif "vnexpress.net" in url:
            container = soup.find(class_=re.compile(r'fck_detail'))
            sapo_tag = soup.find(class_=re.compile(r'description'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        # 3. Tuổi Trẻ & Thanh Niên
        elif "tuoitre.vn" in url or "thanhnien.vn" in url:
            container = soup.find(id="main-detail-body") or soup.find(class_=re.compile(r'detail-content|content-detail'))
            sapo_tag = soup.find(class_=re.compile(r'detail-sapo|sapo'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        # 4. Dân Trí
        elif "dantri.com.vn" in url:
            container = soup.find(class_=re.compile(r'singular-content|dt-news__content'))
            sapo_tag = soup.find(class_=re.compile(r'singular-sapo'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        # 5. VietnamNet
        elif "vietnamnet.vn" in url:
            container = soup.find(id="maincontent") or soup.find(class_=re.compile(r'content-detail|maincontent'))
            sapo_tag = soup.find(class_=re.compile(r'content-detail-sapo'))
            if sapo_tag:
                sapo_text = clean_text(sapo_tag.get_text())

        # Dự phòng chung
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

        if sapo_text and len(sapo_text) > 15:
            content_html_parts.append(f'<p class="font-semibold text-slate-900 text-lg leading-relaxed mb-6 border-b border-slate-100 pb-4">{sapo_text}</p>')

        # Quét tuần tự: đoạn văn, tiêu đề con, danh sách từng bước, code box, ảnh
        for element in container.find_all(['p', 'figure', 'div', 'h2', 'h3', 'h4', 'ul', 'ol', 'pre', 'img']):
            # Ảnh minh họa (Bắt mọi cơ chế Lazy-load)
            if element.name in ['figure', 'img'] or (element.name == 'div' and ('photo' in str(element.get('class', [])).lower() or element.get('type') == 'Photo')):
                img_tag = element if element.name == 'img' else element.find('img')
                if img_tag:
                    src = (
                        img_tag.get('data-src') or 
                        img_tag.get('data-original') or 
                        img_tag.get('data-srcset') or 
                        img_tag.get('src') or ''
                    ).strip()

                    if ' ' in src and src.startswith('http'):
                        src = src.split(' ')[0]

                    # Bổ sung domain cho link tương đối
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://quantrimang.com' + src

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

            # Tiêu đề mục con
            elif element.name in ['h2', 'h3', 'h4']:
                text = clean_text(element.get_text())
                if 5 < len(text) < 150:
                    content_html_parts.append(f'<h3 class="text-xl font-bold text-slate-900 mt-8 mb-3 font-mono">{text}</h3>')

            # Danh sách từng bước thực hiện (Đặc trưng của Quản Trị Mạng)
            elif element.name in ['ul', 'ol']:
                items = element.find_all('li')
                if items:
                    list_items = "".join([f'<li class="mb-2 leading-relaxed">{clean_text(li.get_text())}</li>' for li in items if len(clean_text(li.get_text())) > 5])
                    if list_items:
                        tag_name = "ol" if element.name == "ol" else "ul"
                        list_class = "list-decimal pl-6 my-4 space-y-1 text-slate-700" if tag_name == "ol" else "list-disc pl-6 my-4 space-y-1 text-slate-700"
                        content_html_parts.append(f'<{tag_name} class="{list_class}">{list_items}</{tag_name}>')

            # Đoạn code lập trình / dòng lệnh terminal
            elif element.name == 'pre':
                code_text = clean_text(element.get_text())
                if len(code_text) > 5:
                    content_html_parts.append(f'<pre class="bg-slate-900 text-cyan-300 p-4 rounded-xl overflow-x-auto my-4 font-mono text-xs leading-normal"><code>{code_text}</code></pre>')

            # Đoạn văn bản thông thường
            elif element.name == 'p':
                text = clean_text(element.get_text())
                if len(text) > 30 and not text.lower().startswith(('ảnh:', 'nguồn:', 'theo ')):
                    content_html_parts.append(f'<p class="mb-4 leading-relaxed text-slate-700 text-base sm:text-lg">{text}</p>')

        full_content = "\n".join(content_html_parts)
        return full_content, lead_image

    except Exception as e:
        print(f"      [!] Lỗi trích xuất: {e}")
        return None, None

def analyze_tech_article(title, desc, default_cat):
    title_clean = clean_text(title)
    desc_clean = clean_text(desc)
    content_lower = f"{title_clean} {desc_clean}".lower()

    category = default_cat
    if any(k in content_lower for k in ["hướng dẫn", "thủ thuật", "cách làm", "sửa lỗi", "khắc phục", "quản trị mạng", "windows 11", "router", "cấu hình"]):
        category = "Thủ Thuật & Quản Trị Hệ Thống"
    elif any(k in content_lower for k in ["ai", "trí tuệ nhân tạo", "chatgpt", "openai", "copilot", "gemini", "robot", "llm", "prompt"]):
        category = "Trí tuệ nhân tạo (AI)"
    elif any(k in content_lower for k in ["bảo mật", "hacker", "lừa đảo", "mã độc", "virus", "lỗ hổng", "tấn công mạng", "vpn", "firewall"]):
        category = "An ninh mạng & Bảo mật"
    elif any(k in content_lower for k in ["iphone", "samsung", "laptop", "chip", "máy tính", "bán dẫn", "card màn hình", "pc"]):
        category = "Phần cứng & Thiết bị"
    elif any(k in content_lower for k in ["phần mềm", "windows", "ios", "android", "ứng dụng", "tiện ích"]):
        category = "Phần mềm & Nền tảng"

    summary = desc_clean if len(desc_clean) > 20 else title_clean
    insight = "Kiểm tra kỹ các yêu cầu cấu hình hệ thống và tạo điểm sao lưu (Restore Point) trước khi thao tác."

    if category == "Thủ Thuật & Quản Trị Hệ Thống":
        insight = "Thực hiện cẩn thận theo từng bước hướng dẫn, sao lưu cấu hình file trước khi thay đổi tham số hệ thống."
    elif category == "Trí tuệ nhân tạo (AI)":
        insight = "Tích hợp các prompt mẫu và công cụ AI vào quy trình làm việc thực tế để gia tăng năng suất."
    elif category == "An ninh mạng & Bảo mật":
        insight = "Bật xác thực đa yếu tố (MFA/2FA), tuyệt đối không mở các tệp đính kèm lạ và chủ động cập nhật bản vá bảo mật."
    elif category == "Phần cứng & Thiết bị":
        insight = "Cân nhắc kỹ hiệu năng trên giá thành (P/P) và nhu cầu công việc thực tế trước khi đầu tư nâng cấp."

    return title_clean, summary, insight, category

def crawl_quantrimang(max_articles=6):
    """Cào bài viết trực tiếp từ QuanTriMang.com"""
    print("\n[*] Đang quét nguồn trực tiếp: QuanTriMang.com (Thủ thuật & Quản trị hệ thống)")
    articles_found = []
    try:
        res = requests.get("https://quantrimang.com/", headers=REQUEST_HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                title = clean_text(a.get_text())
                if re.search(r'-\d+$', href) and len(title) > 25:
                    full_link = href if href.startswith('http') else f"https://quantrimang.com{href}"
                    if full_link not in [item['link'] for item in articles_found]:
                        articles_found.append({"title": title, "link": full_link})
                        if len(articles_found) >= max_articles:
                            break
    except Exception as e:
        print(f"    [x] Lỗi truy cập QuanTriMang.com: {e}")

    print(f"    Tìm thấy {len(articles_found)} bài viết mới từ QuanTriMang.com:")
    for item in articles_found:
        title = item["title"]
        url = item["link"]

        if is_article_exists(url):
            print(f"    [-] Đã có trong cơ sở dữ liệu: {title[:40]}...")
            continue

        print(f"    -> Đang trích xuất toàn bộ: {title[:45]}...")
        clean_title, summary, tips, category = analyze_tech_article(title, title, "Thủ Thuật & Quản Trị Hệ Thống")
        full_content, lead_image = scrape_full_article(url)

        if not full_content or len(full_content) < 80:
            full_content = f'<p class="mb-4 leading-relaxed text-slate-700 text-base sm:text-lg">{summary}</p>'

        record = {
            "title": clean_title,
            "summary": summary,
            "tips": tips,
            "category": category,
            "content": full_content,
            "image_url": lead_image,
            "original_url": url
        }

        try:
            db_res = requests.post(SUPABASE_ENDPOINT, headers=SUPABASE_HEADERS, json=record, timeout=10)
            if db_res.status_code in [200, 201]:
                print(f"       ✔ Đã lưu trọn vẹn: [{category}] ({'Có ảnh gốc' if lead_image else 'Ảnh mặc định'})")
            else:
                print(f"       ✖ Lỗi Supabase: {db_res.status_code} - {db_res.text[:80]}")
        except Exception as e:
            print(f"       ✖ Lỗi kết nối: {e}")

        time.sleep(1.5)

# ================= CHẠY QUY TRÌNH THU THẬP =================
print("=== BẮT ĐẦU CÀO DỮ LIỆU CÔNG NGHỆ TIẾNG VIỆT & QUẢN TRỊ MẠNG ===")

# 1. Cào trực tiếp QuanTriMang.com
crawl_quantrimang(max_articles=6)

# 2. Cào các nguồn báo công nghệ Việt Nam
for feed_info in FEEDS:
    source_name = feed_info["source"]
    print(f"\n[*] Đang quét nguồn: {source_name}")

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

        print(f"    -> Đang trích xuất toàn bộ: {original_title[:45]}...")

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

print("\n=== HOÀN TẤT! ĐÃ ĐỒNG BỘ XONG BÀI VIẾT TỪ CÁC NGUỒN TIẾNG VIỆT ===")
