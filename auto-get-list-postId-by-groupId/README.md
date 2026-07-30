# auto-get-list-postId-by-groupId

Script tự động lấy **Post ID** của các bài viết mới nhất từ danh sách Facebook Group, sử dụng **Playwright** để điều khiển trình duyệt Chromium.

---

## Cấu trúc thư mục

```
auto-get-list-postId-by-groupId/
├── main.py       # Script chính
├── requirements.txt          # Thư viện cần cài
└── data/
    ├── cookies.txt           # Cookies đăng nhập Facebook (Netscape format)
    ├── groupid.txt           # Danh sách Group ID cần lấy bài
    ├── postid.txt            # OUTPUT: danh sách Post ID (mỗi dòng 1 ID)
    └── posts.json            # OUTPUT: dữ liệu đầy đủ để debug
```

---

## Cài đặt

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Cách dùng

### Bước 1 — Chuẩn bị cookies

Script hỗ trợ **2 định dạng** cookies, dùng một trong hai cách:

**Cách A — Dán Cookie header string** (đơn giản nhất):
1. Mở `facebook.com`, đăng nhập
2. Mở DevTools (F12) → tab **Application** → **Cookies** → `https://www.facebook.com`
3. Hoặc mở tab **Network**, chọn bất kỳ request nào tới facebook.com → tab **Headers** → copy giá trị `Cookie:`
4. Dán toàn bộ chuỗi vào một dòng trong `data/cookies.txt`:

```
datr=xxx;sb=yyy;c_user=zzz;xs=...
```

**Cách B — Netscape format** (export từ extension):
1. Cài **Cookie-Editor** ([Chrome](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/))
2. Mở `facebook.com`, đăng nhập → click icon extension → **Export** → **Netscape**
3. Lưu toàn bộ nội dung vào `data/cookies.txt`

### Bước 2 — Thêm danh sách Group ID

Mở `data/groupid.txt`, thêm Group ID vào (mỗi ID 1 dòng):

```
# Dòng bắt đầu bằng # là comment, bị bỏ qua
2450244075069818
776506469800802
258940354514985
```

> **Lấy Group ID ở đâu?**  
> Mở trang Group trên Facebook → nhìn URL: `facebook.com/groups/2450244075069818` → ID là phần số cuối URL.

### Bước 3 — Chạy script

```bash
python main.py
```

---

## Output

| File | Mô tả |
|---|---|
| `data/postid.txt` | Danh sách Post ID, mỗi dòng 1 ID. **Append** — không ghi đè lần chạy trước. |
| `data/posts.json` | Dữ liệu đầy đủ gồm `post_id`, `post_link`, `text`, `group_url`. Overwrite mỗi lần chạy. |

---

## Lưu ý

- **Đăng nhập**: Script dùng cookies từ `data/cookies.txt`, không cần mở trình duyệt thủ công.
- **Cookies hết hạn**: Nếu bị redirect về trang login, export lại cookies và thay vào `data/cookies.txt`.
- **Selector thay đổi**: Facebook thay đổi cấu trúc HTML thường xuyên. Nếu script không lấy được bài, mở DevTools (F12), inspect một bài viết và cập nhật selector `[role="article"]` trong hàm `extract_posts_from_group()`.
- **Chỉ dùng tài khoản phụ** — không dùng tài khoản chính. Tự động hoá truy cập Facebook vi phạm ToS của Meta.
