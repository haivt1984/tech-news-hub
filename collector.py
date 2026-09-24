import os
import re
import html
import time
import requests
from bs4 import BeautifulSoup
import sys

# In log trực tiếp trên console GitHub Actions
sys.stdout.reconfigure(line_buffering=True)

# ================= CẤU HÌNH SUPABASE =================
RAW_SUPABASE = os.getenv("SUPABASE_URL", "https://lleeibzegmnycuingzgx.supabase.co")
match = re.search(r'https://[a-zA-Z0-9-]+\.supabase\.co', RAW_SUPABASE)
SUPABASE_URL = match.group(0) if match else "https://lleeibzegmnycuingzgx.supabase.co"

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE"
).strip("[]'\" \t\n\r")

SUPABASE_ENDPOINT = f"{SUPABASE_URL}/rest/v1/tech_articles"
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

# Các chuyên mục nòng cốt của Quản Trị Mạng
QTM_SECTIONS = [
    {"url": "https://quantrimang.com/", "default_cat": "Tiêu Điểm Công Nghệ"},
    {"url": "https://quantrimang.com/cong-nghe", "default_cat": "Làng Công Nghệ"},
    {"url": "https://quantrimang.com/lang-cong-nghe/tri-tue-nhan-tao", "default_cat": "Trí Tuệ Nhân Tạo (AI)"},
    {"url": "https://quantrimang.com/he-thong", "default_cat": "Hệ Thống & Quản Trị"},
    {"url": "https://quantrimang.com/lap-trinh", "default_cat": "Lập Trình & Mã Nguồn"}
]

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
    """Cào chi tiết toàn bộ bài viết từ Quản Trị Mạng"""
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        if res.status_code != 200:
            return None, None

        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # Dọn sạch quảng cáo, widget mua sắm, bình luận
        for junk in soup(['script', 'style', 'iframe', 'header', 'footer', 'nav', 'form', 'aside', 'noscript']):
            junk.decompose()
        for junk in soup.find_all(class_=re.compile(r'relate|box-tag|comment|banner|advert|social|author|breadcrumb|recommend|sticky|box-buy|price-box|affiliate')):
            junk.decompose()

        container = soup.find(id="main-detail-body") or soup.find(class_=re.compile(r'detail-content|content-detail|article-body'))
        if not container:
            container = soup.find('article') or soup.body

        # Lấy đoạn Sapo mở đầu
        sapo_text = ""
        sapo_tag = soup.find(class_=re.compile(r'detail-sapo|sapo|lead'))
        if sapo_tag:
            sapo_text = clean_text(sapo_tag.get_text())

        content_html_parts = []
        lead_image = None
        added_images = set()

        if sapo_text and len(sapo_text) > 15:
            content_html_parts.append(f'<p class="font-semibold text-slate-900 text-lg leading-relaxed mb-6 border-b border-slate-100 pb-4">{sapo_text}</p>')

        # Bóc tách tuần tự: văn bản, danh sách từng bước, code, hình ảnh
        for element in container.find_all(['p', 'figure', 'div', 'h2', 'h3', 'h4', 'ul', 'ol', 'pre', 'img']):
            # Ảnh minh họa (Xử lý mọi cơ chế Lazy-load của Quản Trị Mạng)
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
                            <img src="{src}" alt="{caption}" class="w-full rounded-2xl border border-slate-200 shadow-xs object-cover max-h-[520px]" loading="lazy" onerror="this.style.display='none'">
                            {f'<figcaption class="text-xs text-center text-slate-500 mt-2 font-mono italic">{caption}</figcaption>' if caption else ''}
                        </figure>
                        """)

            # Tiêu đề mục con
            elif element.name in ['h2', 'h3', 'h4']:
                text = clean_text(element.get_text())
                if 5 < len(text) < 150:
                    content_html_parts.append(f'<h3 class="text-xl font-bold text-slate-900 mt-8 mb-3 font-mono">{text}</h3>')

            # Danh sách từng bước thực hiện
            elif element.name in ['ul', 'ol']:
                items = element.find_all('li')
                if items:
                    list_items = "".join([f'<li class="mb-2 leading-relaxed">{clean_text(li.get_text())}</li>' for li in items if len(clean_text(li.get_text())) > 5])
                    if list_items:
                        tag_name = "ol" if element.name == "ol" else "ul"
                        list_class = "list-decimal pl-6 my-4 space-y-1 text-slate-700" if tag_name == "ol" else "list-disc pl-6 my-4 space-y-1 text-slate-700"
                        content_html_parts.append(f'<{tag_name} class="{list_class}">{list_items}</{tag_name}>')

            # Hộp code / Lệnh command line
            elif element.name == 'pre':
                code_text = clean_text(element.get_text())
                if len(code_text) > 5:
                    content_html_parts.append(f'<pre class="bg-[#1e293b] text-cyan-300 p-4 rounded-xl overflow-x-auto my-4 font-mono text-xs leading-normal"><code>{code_text}</code></pre>')

            # Đoạn văn bản
            elif element.name == 'p':
                text = clean_text(element.get_text())
                if len(text) > 30 and not text.lower().startswith(('ảnh:', 'nguồn:', 'theo ')):
                    content_html_parts.append(f'<p class="mb-4 leading-relaxed text-slate-700 text-base sm:text-lg">{text}</p>')

        full_content = "\n".join(content_html_parts)
        return full_content, lead_image

    except Exception as e:
        print(f"      [!] Lỗi trích xuất: {e}")
        return None, None

def analyze_qtm_article(title, default_cat):
    title_clean = clean_text(title)
    content_lower = title_clean.lower()

    category = default_cat
    if any(k in content_lower for k in ["ai", "chatgpt", "openai", "copilot", "gemini", "prompt", "deep research"]):
        category = "Trí Tuệ Nhân Tạo (AI)"
    elif any(k in content_lower for k in ["bảo mật", "hacker", "virus", "lỗ hổng", "mã độc", "vpn", "mật khẩu"]):
        category = "An Ninh & Bảo Mật"
    elif any(k in content_lower for k in ["hướng dẫn", "thủ thuật", "cách", "sửa lỗi", "windows", "ios", "android"]):
        category = "Thủ Thuật & Hệ Thống"
    elif any(k in content_lower for k in ["python", "code", "lập trình", "sql", "html", "css", "javascript"]):
        category = "Lập Trình & Phát Triển"
    elif any(k in content_lower for k in ["quản trị mạng", "router", "wifi", "ip", "cisco", "switch", "dns"]):
        category = "Quản Trị Mạng & Mạng Máy Tính"

    summary = title_clean
    insight = "Thực hiện cẩn thận theo từng bước hướng dẫn, sao lưu cấu hình hệ thống trước khi thao tác."

    if category == "Trí Tuệ Nhân Tạo (AI)":
        insight = "Ứng dụng các prompt mẫu và công cụ AI mới vào công việc thực tế để tự động hóa tác vụ."
    elif category == "An Ninh & Bảo Mật":
        insight = "Bật xác thực đa yếu tố (2FA), không nhấp liên kết lạ và cập nhật bản vá hệ điều hành định kỳ."
    elif category == "Quản Trị Mạng & Mạng Máy Tính":
        insight = "Kiểm tra kỹ sơ đồ phân dải IP, subnet mask và tạo bản backup file config thiết bị mạng."

    return title_clean, summary, insight, category

# ================= QUY TRÌNH THU THẬP TỪ QUANTRIMANG =================
print("=== BẮT ĐẦU CÀO BÀI VIẾT CHUYÊN BIỆT TỪ QUANTRIMANG.COM ===")

unique_articles = []
seen_urls = set()

for sec in QTM_SECTIONS:
    print(f"\n[*] Đang quét danh mục: {sec['default_cat']} ({sec['url']})")
    try:
        res = requests.get(sec["url"], headers=REQUEST_HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                title = clean_text(a.get_text())
                # Bắt các link bài viết có cấu trúc id bài ở cuối đuôi (-123456)
                if re.search(r'-\d+$', href) and len(title) > 25:
                    full_link = href if href.startswith('http') else f"https://quantrimang.com{href}"
                    if full_link not in seen_urls:
                        seen_urls.add(full_link)
                        unique_articles.append({
                            "title": title,
                            "url": full_link,
                            "cat": sec["default_cat"]
                        })
    except Exception as e:
        print(f"    [x] Lỗi truy cập: {e}")

print(f"\n=> Đã phát hiện tổng cộng {len(unique_articles)} bài viết từ Quản Trị Mạng.")
print("Bắt đầu trích xuất và đồng bộ vào Supabase (giới hạn 15 bài mới nhất mỗi lần chạy):")

saved_count = 0
for item in unique_articles[:15]:
    title = item["title"]
    url = item["url"]

    if is_article_exists(url):
        print(f"  [-] Đã tồn tại: {title[:40]}...")
        continue

    print(f"  -> Đang bóc tách bài: {title[:45]}...")
    clean_title, summary, tips, category = analyze_qtm_article(title, item["cat"])
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
            print(f"     ✔ Đã lưu thành công: [{category}] ({'Có ảnh' if lead_image else 'Ảnh mặc định'})")
            saved_count += 1
        else:
            print(f"     ✖ Lỗi Supabase: {db_res.status_code}")
    except Exception as e:
        print(f"     ✖ Lỗi kết nối: {e}")

    time.sleep(1.2)

print(f"\n=== HOÀN TẤT! ĐÃ ĐỒNG BỘ THÀNH CÔNG {saved_count} BÀI TỪ QUANTRIMANG.COM ===")
