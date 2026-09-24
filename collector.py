import os
import re
import html
import time
import requests
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(line_buffering=True)

# ================= CẤU HÌNH KẾT NỐI SUPABASE =================
RAW_SUPABASE = os.getenv("SUPABASE_URL", "https://lleeibzegmnycuingzgx.supabase.co")
match = re.search(r'https://[a-zA-Z0-9-]+\.supabase\.co', RAW_SUPABASE)
SUPABASE_URL = match.group(0) if match else "https://lleeibzegmnycuingzgx.supabase.co"

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE"
).strip("[]'\" \t\n\r")

# Số lượng bài viết tối đa cần nạp mỗi lần chạy (mặc định 25 bài mới nhất)
TARGET_ARTICLES = int(os.getenv("TARGET_ARTICLES", 25))

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

# DANH SÁCH CÁC CHUYÊN MỤC TRỌNG ĐIỂM ĐƯỢC CHỌN LỌC TỪ FILE EXCEL
QTM_SECTIONS = [
    # 1. AI & Hệ sinh thái mô hình lớn
    {"url": "https://quantrimang.com/ai", "cat": "AI", "sub": "Hệ Sinh Thái AI"},
    {"url": "https://quantrimang.com/chatgpt", "cat": "AI", "sub": "ChatGPT"},
    {"url": "https://quantrimang.com/claude", "cat": "AI", "sub": "Claude"},
    {"url": "https://quantrimang.com/gemini", "cat": "AI", "sub": "Gemini"},
    {"url": "https://quantrimang.com/copilot", "cat": "AI", "sub": "Copilot"},
    {"url": "https://quantrimang.com/grok", "cat": "AI", "sub": "Grok"},
    {"url": "https://quantrimang.com/perplexity", "cat": "AI", "sub": "Perplexity"},
    {"url": "https://quantrimang.com/cursor", "cat": "AI", "sub": "Cursor"},

    # 2. Thư viện Prompt & Hướng dẫn làm chủ AI
    {"url": "https://quantrimang.com/ai-prompt", "cat": "Prompt", "sub": "Thư Viện Prompt"},
    {"url": "https://quantrimang.com/prompt-it", "cat": "Prompt", "sub": "Prompt Lập Trình"},
    {"url": "https://quantrimang.com/lam-chu-ai", "cat": "Hướng dẫn AI", "sub": "Hướng Dẫn AI"},
    {"url": "https://quantrimang.com/ai-cho-nguoi-moi", "cat": "Hướng dẫn AI", "sub": "AI Cho Người Mới"},
    {"url": "https://quantrimang.com/ai-cho-van-phong", "cat": "Hướng dẫn AI", "sub": "AI Cho Văn Phòng"},
    {"url": "https://quantrimang.com/ai-cho-lap-trinh", "cat": "Hướng dẫn AI", "sub": "AI Cho Lập Trình"},
    {"url": "https://quantrimang.com/workflow", "cat": "Workflow", "sub": "AI Automation"},

    # 3. Công nghệ, Hệ thống & Bảo mật
    {"url": "https://quantrimang.com/cong-nghe", "cat": "Công nghệ", "sub": "Làng Công Nghệ"},
    {"url": "https://quantrimang.com/cong-nghe/he-thong", "cat": "Công nghệ", "sub": "Hệ Thống & Quản Trị"},
    {"url": "https://quantrimang.com/cong-nghe/bao-mat", "cat": "Công nghệ", "sub": "An Ninh & Bảo Mật"},
    {"url": "https://quantrimang.com/cong-nghe/phan-cung", "cat": "Công nghệ", "sub": "Phần Cứng & Thiết Bị"},
    {"url": "https://quantrimang.com/cong-nghe/linux-os", "cat": "Công nghệ", "sub": "Linux & Server"},

    # 4. Học CNTT & Mã nguồn
    {"url": "https://quantrimang.com/hoc", "cat": "Học CNTT", "sub": "Học Lập Trình"},
    {"url": "https://quantrimang.com/hoc/hoc-python", "cat": "Học CNTT", "sub": "Python"},
    {"url": "https://quantrimang.com/hoc/hoc-excel", "cat": "Học CNTT", "sub": "Hàm Excel"},
    {"url": "https://quantrimang.com/hoc/vibe-coding", "cat": "Học CNTT", "sub": "Vibe Coding với AI"}
]

def clean_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()

def is_article_exists(url):
    try:
        check_url = f"{SUPABASE_ENDPOINT}?original_url=eq.{requests.utils.quote(url)}&select=id"
        res = requests.get(check_url, headers=SUPABASE_HEADERS, timeout=8)
        if res.status_code == 200 and len(res.json()) > 0:
            return True
    except Exception as e:
        print(f"      [!] Lỗi kiểm tra tồn tại: {e}")
    return False

def scrape_full_article(url):
    """Trích xuất trọn vẹn văn bản, từng bước hướng dẫn, code snippets và toàn bộ hình ảnh gốc"""
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        if res.status_code != 200:
            return None, None

        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # Dọn sạch các phần tử rác
        for junk in soup(['script', 'style', 'iframe', 'header', 'footer', 'nav', 'form', 'aside', 'noscript']):
            junk.decompose()
        for junk in soup.find_all(class_=re.compile(r'relate|box-tag|comment|banner|advert|social|author|breadcrumb|recommend|sticky|box-buy|price-box|affiliate')):
            junk.decompose()

        container = soup.find(id="main-detail-body") or soup.find(class_=re.compile(r'detail-content|content-detail|article-body'))
        if not container:
            container = soup.find('article') or soup.body

        sapo_text = ""
        sapo_tag = soup.find(class_=re.compile(r'detail-sapo|sapo|lead'))
        if sapo_tag:
            sapo_text = clean_text(sapo_tag.get_text())

        content_html_parts = []
        lead_image = None
        added_images = set()

        if sapo_text and len(sapo_text) > 15:
            content_html_parts.append(f'<p class="font-semibold text-slate-900 text-lg leading-relaxed mb-6 border-b border-slate-100 pb-4">{sapo_text}</p>')

        for element in container.find_all(['p', 'figure', 'div', 'h2', 'h3', 'h4', 'ul', 'ol', 'pre', 'img']):
            # Bóc tách hình ảnh (kèm xử lý lazy-load)
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

            # Danh sách từng bước thực hiện (ol/ul)
            elif element.name in ['ul', 'ol']:
                items = element.find_all('li')
                if items:
                    list_items = "".join([f'<li class="mb-2 leading-relaxed">{clean_text(li.get_text())}</li>' for li in items if len(clean_text(li.get_text())) > 5])
                    if list_items:
                        tag_name = "ol" if element.name == "ol" else "ul"
                        list_class = "list-decimal pl-6 my-4 space-y-1 text-slate-700" if tag_name == "ol" else "list-disc pl-6 my-4 space-y-1 text-slate-700"
                        content_html_parts.append(f'<{tag_name} class="{list_class}">{list_items}</{tag_name}>')

            # Hộp code snippet / terminal command
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

def analyze_article(title, default_cat, sub_cat):
    title_clean = clean_text(title)
    content_lower = title_clean.lower()

    # Nhận diện chuyên mục chi tiết dựa trên phân loại menu
    category = default_cat
    if any(k in content_lower for k in ["prompt", "câu lệnh", "mẫu prompt"]):
        category = "Prompt"
    elif any(k in content_lower for k in ["chatgpt", "gpt-4", "gpt-5", "openai"]):
        category = "ChatGPT"
    elif any(k in content_lower for k in ["claude", "anthropic", "sonnet"]):
        category = "Claude"
    elif any(k in content_lower for k in ["gemini", "google deepmind"]):
        category = "Gemini"
    elif any(k in content_lower for k in ["copilot", "microsoft 365 copilot"]):
        category = "Copilot"
    elif any(k in content_lower for k in ["workflow", "n8n", "zapier", "automation"]):
        category = "Workflow"
    elif any(k in content_lower for k in ["bảo mật", "hacker", "virus", "lỗ hổng", "mã độc", "vpn"]):
        category = "Bảo Mật"
    elif any(k in content_lower for k in ["python", "hàm excel", "sql", "code", "lập trình"]):
        category = "Học CNTT"

    summary = title_clean
    insight = f"Chuyên mục [{sub_cat}]: Thực hiện theo từng bước hướng dẫn, lưu ý sao lưu hoặc kiểm chứng kết quả trước khi đưa vào môi trường làm việc."

    if category in ["AI", "ChatGPT", "Claude", "Gemini", "Copilot"]:
        insight = "Thực hành thử nghiệm kết hợp prompt chi tiết để tối ưu độ chính xác và giảm thiểu hiện tượng ảo giác (hallucination) của AI."
    elif category == "Prompt":
        insight = "Áp dụng công thức đóng vai (Role) + Mục tiêu (Goal) + Định dạng mong muốn (Format) để câu lệnh đạt hiệu quả cao nhất."
    elif category == "Bảo Mật":
        insight = "Kích hoạt xác thực 2 lớp (2FA/MFA) và kiểm tra kỹ địa chỉ nguồn trước khi thao tác các đường link hoặc file đính kèm."

    return title_clean, summary, insight, category

# ================= QUY TRÌNH THU THẬP =================
print(f"=== BẮT ĐẦU CÀO BÀI VIẾT THEO DANH MỤC QUANTRI MẠNG (MỤC TIÊU: {TARGET_ARTICLES} BÀI) ===")

unique_articles = []
seen_urls = set()

for sec in QTM_SECTIONS:
    if len(unique_articles) >= TARGET_ARTICLES * 2:
        break

    print(f"\n[*] Đang quét danh mục: {sec['sub']} ({sec['url']})")
    try:
        res = requests.get(sec["url"], headers=REQUEST_HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                title = clean_text(a.get_text())
                if re.search(r'-\d+$', href) and len(title) > 25:
                    full_link = href if href.startswith('http') else f"https://quantrimang.com{href}"
                    if full_link not in seen_urls:
                        seen_urls.add(full_link)
                        unique_articles.append({
                            "title": title,
                            "url": full_link,
                            "cat": sec["cat"],
                            "sub": sec["sub"]
                        })
    except Exception as e:
        print(f"    [x] Lỗi truy cập: {e}")
    time.sleep(0.3)

print(f"\n=> Tìm thấy {len(unique_articles)} bài viết mới từ hệ thống menu.")
print(f"Bắt đầu nạp bài vào Supabase:\n")

saved_count = 0
for item in unique_articles:
    if saved_count >= TARGET_ARTICLES:
        break

    title = item["title"]
    url = item["url"]

    if is_article_exists(url):
        continue

    print(f"[{saved_count + 1}/{TARGET_ARTICLES}] Trích xuất: {title[:45]}...")
    clean_title, summary, tips, category = analyze_article(title, item["cat"], item["sub"])
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
            saved_count += 1
            print(f"       ✔ Đã lưu: [{category}]")
        else:
            print(f"       ✖ Lỗi Supabase: {db_res.status_code}")
    except Exception as e:
        print(f"       ✖ Lỗi mạng: {e}")

    time.sleep(1.0)

print(f"\n=== HOÀN TẤT! ĐÃ LƯU {saved_count} BÀI VIẾT VÀO SUPABASE ===")
