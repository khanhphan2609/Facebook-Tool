"""
Facebook Group Scraper - Lấy post ID từ danh sách Group Facebook.

============================================================================
CẢNH BÁO (đọc trước khi dùng):
- Việc tự động hóa truy cập/thu thập dữ liệu Facebook VI PHẠM Điều khoản
  dịch vụ (ToS) của Facebook. Tài khoản dùng để chạy script này có thể bị
  Facebook tạm khóa hoặc khóa vĩnh viễn bất cứ lúc nào.
- Nên dùng TÀI KHOẢN PHỤ, không dùng tài khoản chính/công việc quan trọng.
- Facebook thay đổi cấu trúc HTML thường xuyên -> script có thể cần cập
  nhật lại các CSS selector theo thời gian.
- Chỉ nên dùng cho mục đích cá nhân, hợp lệ (theo dõi group bạn đã tham
  gia), không dùng để thu thập dữ liệu cá nhân người khác trái phép.
- Không chạy quá nhanh / quá nhiều group liên tục để giảm nguy cơ bị
  Facebook gắn cờ là bot.
============================================================================

Cách hoạt động (tổng quan):
1. Đọc danh sách link Group từ file data/group_fb_link.txt (mỗi link 1 dòng).
2. Đọc cookies Facebook từ file data/cookies.txt (định dạng Netscape).
   - Export bằng extension: Cookie-Editor, EditThisCookie, Get cookies.txt LOCALLY
   - Mở facebook.com trên trình duyệt thường, export toàn bộ cookies ra file txt
3. Nạp cookies vào Playwright context -> truy cập FB như đã đăng nhập sẵn,
   không cần mở trình duyệt / nhập tay.
4. Với mỗi Group, mở trang, cuộn để load bài viết (infinite scroll), rồi
   trích xuất post ID + permalink của các bài mới nhất.
5. Lưu kết quả:
   - data/postid.txt   : danh sách post ID, mỗi dòng 1 ID (append, không ghi đè)
   - data/posts.json   : dữ liệu đầy đủ (text + link + id) để debug/kiểm tra

Yêu cầu cài đặt:
    pip install playwright
    playwright install chromium

Cách lấy cookies.txt:
    1. Cài extension "Cookie-Editor" (Chrome/Firefox) hoặc "Get cookies.txt LOCALLY"
    2. Mở facebook.com, đăng nhập bình thường
    3. Click icon extension -> Export -> Netscape format -> lưu vào data/cookies.txt
"""

import json
import re
import time
import random
from pathlib import Path
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout


# ---------------------------------------------------------------------------
# CẤU HÌNH
# ---------------------------------------------------------------------------

# File cookies đăng nhập Facebook (định dạng Netscape - export từ trình duyệt)
COOKIES_FILE = "data/cookies.txt"

# File chứa danh sách Group ID Facebook (mỗi ID 1 dòng, # là comment)
GROUP_IDS_FILE = "data/groupid.txt"

FACEBOOK_GROUP_BASE_URL = "https://www.facebook.com/groups/"

# Số bài mới nhất cần lấy mỗi group
POSTS_PER_GROUP = 10

# Output
POSTID_FILE = "data/postid.txt"      # danh sách post ID, mỗi dòng 1 ID
POSTS_JSON_FILE = "data/posts.json"  # dữ liệu đầy đủ để debug/kiểm tra

# Khoảng nghỉ ngẫu nhiên (giây) giữa các thao tác - giả lập hành vi người thật
MIN_DELAY = 1.5
MAX_DELAY = 3.5


# ---------------------------------------------------------------------------
# TIỆN ÍCH
# ---------------------------------------------------------------------------

def human_delay(a: float = MIN_DELAY, b: float = MAX_DELAY) -> None:
    """Nghỉ một khoảng thời gian ngẫu nhiên, giả lập hành vi người dùng thật."""
    time.sleep(random.uniform(a, b))


def ensure_data_dir() -> None:
    """Đảm bảo thư mục data/ tồn tại (tạo nếu chưa có)."""
    Path("data").mkdir(parents=True, exist_ok=True)


def load_group_urls(filepath: str = GROUP_IDS_FILE) -> list:
    """
    Đọc danh sách Group ID từ file txt rồi tự ghép thành URL Facebook.
    - Mỗi dòng là một Group ID (chỉ số), ví dụ: 2450244075069818
    - Bỏ qua dòng trống và dòng bắt đầu bằng #
    - URL được tự ghép: https://www.facebook.com/groups/{group_id}
    """
    path = Path(filepath)
    if not path.exists():
        print(f"[LỖI] Không tìm thấy file: {filepath}")
        print( "      Hãy thêm Group ID vào file (định dạng: mỗi dòng 1 ID số).")
        return []

    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            group_id = line.strip()
            if group_id and not group_id.startswith("#"):
                urls.append(f"{FACEBOOK_GROUP_BASE_URL}{group_id}")

    print(f"Đã tải {len(urls)} group từ {filepath}")
    return urls


def extract_post_id(url) -> str:
    """
    Trích xuất post ID từ các dạng URL phổ biến của Facebook:
      - https://www.facebook.com/groups/123456/posts/789012/
      - https://www.facebook.com/groups/123456/permalink/789012/
      - https://www.facebook.com/permalink.php?story_fbid=789012&id=123456
      - https://www.facebook.com/groups/123456?post_id=789012
    Trả về chuỗi số (post ID) nếu tìm được, ngược lại trả None.
    """
    if not url:
        return None

    patterns = [
        r"/posts/(\d+)",            # .../posts/789012
        r"/permalink/(\d+)",        # .../permalink/789012
        r"story_fbid=(\d+)",        # ...?story_fbid=789012
        r"post_id=(\d+)",           # ...?post_id=789012
        r"multi_permalinks=(\d+)",  # link chia sẻ multi-post
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


# ---------------------------------------------------------------------------
# BƯỚC 1: NẠP COOKIES TỪ FILE
# ---------------------------------------------------------------------------

def _parse_cookie_header_string(cookie_str: str) -> list:
    """
    Parse chuỗi cookie dạng HTTP header:
        name1=value1;name2=value2;...
    Trả về danh sách dict cookie cho Playwright, gán domain .facebook.com.
    """
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, _, value = part.partition("=")
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        cookies.append({
            "name": name,
            "value": value,
            "domain": ".facebook.com",
            "path": "/",
            "secure": True,
            "httpOnly": False,
        })
    return cookies


def _parse_netscape_line(line: str):
    """
    Parse 1 dòng định dạng Netscape (tab-separated, 7 trường):
        domain  include_subdomains  path  secure  expiry  name  value
    Trả về dict cookie hoặc None nếu dòng không hợp lệ.
    """
    parts = line.split("\t")
    if len(parts) < 7:
        return None
    domain, _, path_val, secure, expiry, name, value = parts[:7]
    cookie = {
        "name": name,
        "value": value,
        "domain": domain,
        "path": path_val,
        "secure": secure.upper() == "TRUE",
        "httpOnly": False,
    }
    try:
        exp = int(expiry)
        if exp > 0:
            cookie["expires"] = exp
    except (ValueError, TypeError):
        pass
    return cookie


def load_cookies_from_txt(filepath: str = COOKIES_FILE) -> list:
    """
    Đọc cookies từ file, tự động nhận diện 2 định dạng:

    1. Netscape (tab-separated 7 cột) - export từ Cookie-Editor / curl:
           .facebook.com<TAB>TRUE<TAB>/<TAB>TRUE<TAB>1999999999<TAB>c_user<TAB>123

    2. HTTP Cookie header string - copy trực tiếp từ DevTools / browser:
           datr=xxx;sb=yyy;c_user=zzz;xs=...

    Dòng bắt đầu bằng # hoặc rỗng -> bỏ qua.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file cookies: {filepath}\n"
            f"Hãy dán chuỗi cookies Facebook vào file này.\n"
            f"Có thể dán trực tiếp dạng: name1=val1;name2=val2;..."
        )

    cookies = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "\t" in line:
                # Định dạng Netscape (có tab phân cách)
                cookie = _parse_netscape_line(line)
                if cookie:
                    cookies.append(cookie)
            else:
                # Định dạng HTTP Cookie header string (name=val;name=val;...)
                parsed = _parse_cookie_header_string(line)
                cookies.extend(parsed)

    print(f"Đã đọc {len(cookies)} cookies từ {filepath}")
    return cookies


def apply_cookies(context, cookies: list) -> None:
    """
    Nạp danh sách cookies vào Playwright BrowserContext.
    Sau bước này, mọi request từ context sẽ gửi kèm cookies -> truy cập
    Facebook như đã đăng nhập sẵn.
    """
    context.add_cookies(cookies)


# ---------------------------------------------------------------------------
# BƯỚC 2: CUỘN TRANG ĐỂ TẢI THÊM BÀI VIẾT (Facebook infinite scroll)
# ---------------------------------------------------------------------------

def scroll_to_load_posts(page: Page, min_posts_needed: int, max_scrolls: int = 15) -> int:
    """
    Cuộn trang nhiều lần để trigger Facebook load thêm bài viết.
    Dừng sớm nếu đã có đủ số bài cần lấy, hoặc khi đạt số lần cuộn tối đa.
    Trả về số bài viết hiện có trên DOM sau khi cuộn xong.
    """
    for _ in range(max_scrolls):
        current_count = page.locator('[role="article"]').count()
        if current_count >= min_posts_needed:
            break
        page.mouse.wheel(0, 2000)
        human_delay()

    return page.locator('[role="article"]').count()


# ---------------------------------------------------------------------------
# BƯỚC 3: TRÍCH XUẤT DỮ LIỆU BÀI VIẾT TỪ 1 GROUP
# ---------------------------------------------------------------------------

def extract_posts_from_group(page: Page, group_url: str, limit: int) -> list:
    """
    Mở trang group, cuộn để load bài viết, rồi trích xuất text + post ID
    của `limit` bài viết mới nhất.

    Kiểm tra redirect về trang login (session hết hạn hoặc không có quyền
    truy cập group). Nếu bị redirect, bỏ qua group này và trả về [].

    LƯU Ý: selector [role="article"] dựa theo cấu trúc HTML hiện tại của
    Facebook. Nếu Facebook thay đổi cấu trúc, cần inspect lại (F12) và cập
    nhật selector cho phù hợp.
    """
    print(f"\nĐang mở group: {group_url}")
    page.goto(group_url, wait_until="domcontentloaded", timeout=30_000)
    human_delay(3, 5)  # đợi trang load nội dung ban đầu

    # Kiểm tra nếu bị redirect về trang login (session hết hạn)
    if "login" in page.url:
        print("  [CẢNH BÁO] Bị chuyển hướng về trang login!")
        print("  => Session có thể đã hết hạn. Xóa fb_session.json và đăng nhập lại.")
        return []

    # Cuộn để đảm bảo có đủ số bài viết cần lấy trên DOM
    total_found = scroll_to_load_posts(page, min_posts_needed=limit)
    print(f"  Tìm thấy {total_found} bài trên DOM, lấy {min(limit, total_found)} bài đầu.")

    posts_data = []
    articles = page.locator('[role="article"]')

    for i in range(min(limit, total_found)):
        article = articles.nth(i)

        # Lấy toàn bộ text hiển thị của bài viết
        try:
            text_content = article.inner_text(timeout=5000).strip()
        except PWTimeout:
            text_content = ""

        # Tìm link permalink của bài viết (href chứa /posts/ hoặc /permalink/)
        post_link = None
        try:
            for link in article.locator("a").all():
                href = link.get_attribute("href") or ""
                if "/posts/" in href or "/permalink/" in href:
                    post_link = href
                    break
        except Exception:
            pass

        post_id = extract_post_id(post_link)

        posts_data.append({
            "group_url": group_url,
            "index": i + 1,
            "post_id": post_id,
            "post_link": post_link,
            "text": text_content[:2000],  # cắt bớt nếu quá dài
        })

        if post_id:
            print(f"  [{i + 1}] post_id={post_id}")
        else:
            print(f"  [{i + 1}] Không lấy được post_id (link: {post_link})")

    return posts_data


# ---------------------------------------------------------------------------
# BƯỚC 4: LƯU KẾT QUẢ
# ---------------------------------------------------------------------------

def save_results(all_posts: list) -> None:
    """
    Lưu kết quả ra 2 file:
    - data/postid.txt  : danh sách post ID (mỗi dòng 1 ID, bỏ qua None, append)
    - data/posts.json  : dữ liệu đầy đủ để debug/kiểm tra (overwrite)
    """
    ensure_data_dir()

    # Gom tất cả post_id hợp lệ (không None, không trùng trong lần chạy này)
    seen = set()
    post_ids = []
    for post in all_posts:
        pid = post.get("post_id")
        if pid and pid not in seen:
            seen.add(pid)
            post_ids.append(pid)

    # Ghi file post ID - append để không mất dữ liệu các lần chạy trước
    with open(POSTID_FILE, "a", encoding="utf-8") as f:
        for pid in post_ids:
            f.write(pid + "\n")

    # Ghi file JSON đầy đủ (overwrite - chỉ giữ lần chạy gần nhất)
    with open(POSTS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    print(f"\nĐã lưu {len(post_ids)} post ID vào {POSTID_FILE}")
    print(f"Đã lưu dữ liệu đầy đủ vào {POSTS_JSON_FILE}")


# ---------------------------------------------------------------------------
# HÀM CHÍNH
# ---------------------------------------------------------------------------

def scrape_all_groups() -> None:
    """
    Luồng chính:
    1. Đọc danh sách group URL từ data/group_fb_link.txt
    2. Đọc cookies từ data/cookies.txt và nạp vào Playwright context
    3. Duyệt từng group, trích xuất post ID
    4. Lưu kết quả vào data/postid.txt và data/posts.json
    """
    ensure_data_dir()

    # Bước 1: Đọc danh sách group
    group_urls = load_group_urls()
    if not group_urls:
        print("Không có group nào để xử lý. Hãy thêm link vào data/group_fb_link.txt")
        return

    # Bước 2: Đọc cookies
    cookies = load_cookies_from_txt()

    all_posts = []

    with sync_playwright() as p:
        # headless=False: giảm nguy cơ bị Facebook phát hiện là bot
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        # Nạp cookies vào context -> truy cập FB như đã đăng nhập
        apply_cookies(context, cookies)

        page = context.new_page()

        # Bước 3: Duyệt từng group
        for idx, group_url in enumerate(group_urls, start=1):
            print(f"\n[{idx}/{len(group_urls)}] {group_url}")
            try:
                posts = extract_posts_from_group(page, group_url, POSTS_PER_GROUP)
                all_posts.extend(posts)
                ok_count = sum(1 for p in posts if p["post_id"])
                print(f"  => Lấy được {len(posts)} bài, {ok_count} có post_id.")
            except Exception as e:
                print(f"  [LỖI] Không xử lý được group này: {e}")

            # Nghỉ giữa các group để tránh bị coi là bot
            if idx < len(group_urls):
                delay = random.uniform(5, 10)
                print(f"  Nghỉ {delay:.1f}s trước khi sang group tiếp theo...")
                time.sleep(delay)

        browser.close()

    # Bước 4: Lưu kết quả
    save_results(all_posts)
    print("\nHoàn tất!")


if __name__ == "__main__":
    scrape_all_groups()
