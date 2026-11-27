"""Playwright-powered Threads post & comment scraper with GraphQL/SSR extraction and spam filtering."""
from __future__ import annotations

import hashlib
import json
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import threading
from typing import Any, Callable
import urllib.request
from urllib.parse import urlsplit, urlunsplit

from ..core.models import CommentMode, SegmentItem

# The login and scrape workers share one app profile, which Edge can open only once.
_THREADS_BROWSER_LOCK = threading.Lock()

_SPAM_PATTERNS = re.compile(
    r"(shopee\.vn|shope\.ee|s\.shopee|lazada\.vn|tiktok\.com/@|bio\s+link|link\s+mua|giỏ\s+hàng|aff|pass\s+đồ)",
    re.IGNORECASE,
)


def is_spam_comment(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if _SPAM_PATTERNS.search(t):
        return True
    # Pure punctuation, single dot, or "chấm / hóng" noise
    alnum = re.sub(r"[^\wà-ỹÀ-Ỹ]", "", t)
    if len(alnum) < 3 or alnum.lower() in {"cham", "chấm", "hong", "hóng", "up"}:
        return True
    return False


def validate_threads_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme != "https" or parsed.hostname not in {
        "threads.com", "www.threads.com", "threads.net", "www.threads.net",
    } or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Hãy nhập URL HTTPS của bài viết trên threads.com hoặc threads.net.")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def optional_count(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = int(value)
        return result if result >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def open_threads_login_session(profile_dir: Path) -> None:
    """Let the user sign in through native Edge, using only the app-owned profile."""
    candidates = [Path(os.environ[key]) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
                  for key in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA") if os.environ.get(key)]
    candidates.append(Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"))
    executable = (shutil.which("msedge") or shutil.which("microsoft-edge") or shutil.which("microsoft-edge-stable")
                  or next((str(path) for path in candidates if path.is_file()), None))
    if executable is None:
        raise RuntimeError("Không tìm thấy Microsoft Edge. Hãy kiểm tra Edge đã được cài trên máy.")

    with _THREADS_BROWSER_LOCK:
        profile_dir.mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen(
            [executable, f"--user-data-dir={profile_dir.resolve()}", "--new-window",
             "--disable-background-mode", "--no-first-run", "--no-default-browser-check",
             "https://www.threads.com/login"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        # Keep scraping locked until all windows of this separate Edge instance close.
        if process.wait() != 0:
            raise RuntimeError("Edge kết thúc bất thường. Đóng cửa sổ Edge của app rồi thử đăng nhập lại.")


def scrape_threads_url(
    url: str,
    *,
    profile_dir: Path,
    media_cache_dir: Path,
    comment_mode: str = CommentMode.TOP_LIKES_WITH_AUTHOR.value,
    max_comments: int = 6,
    comment_sort: str = "likes",
    candidates: list[dict[str, Any]] | None = None,
    coverage: dict[str, Any] | None = None,
    cancelled: Callable[[], bool] = lambda: False,
) -> tuple[str, list[SegmentItem]]:
    """Read Threads directly in Edge, scroll ten times, and rank loaded replies locally."""
    from playwright.sync_api import sync_playwright

    url = validate_threads_url(url)
    if cancelled():
        raise RuntimeError("Đã dừng lấy bình luận.")
    if candidates:
        return select_thread_segments(candidates, media_cache_dir, comment_mode, comment_sort, max_comments)
    captured_payloads: list[Any] = []

    dom_fallback: list[dict[str, Any]] = []
    with _THREADS_BROWSER_LOCK, sync_playwright() as p:
        use_persistent = (profile_dir / "Default").exists() or any(profile_dir.glob("*Cookie*"))
        if use_persistent:
            ctx = p.chromium.launch_persistent_context(
                channel="msedge",
                chromium_sandbox=True,
                user_data_dir=str(profile_dir),
                headless=True,
                viewport={"width": 1280, "height": 1600},
                args=["--disable-blink-features=AutomationControlled"],
            )
        else:
            browser = p.chromium.launch(channel="msedge", chromium_sandbox=True, headless=True, args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 1600},
                locale="vi-VN",
            )

        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            def _on_response(resp) -> None:
                if "graphql" in resp.url or "api/v1" in resp.url:
                    try:
                        captured_payloads.append(resp.json())
                    except Exception:
                        pass

            page.on("response", _on_response)
            page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_timeout(2500)
            dom_fallback.extend(_extract_dom_fallback(page))
            for _ in range(10):
                if cancelled():
                    raise RuntimeError("Đã dừng lấy bình luận.")
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(900)
                dom_fallback.extend(_extract_dom_fallback(page))

            scripts_json = page.evaluate(
                """() => Array.from(document.querySelectorAll('script[type="application/json"]'))
                            .map(s => s.textContent).filter(Boolean)"""
            )
            for raw_s in scripts_json:
                if "thread_items" in raw_s or "text_post_app_info" in raw_s:
                    try:
                        captured_payloads.append(json.loads(raw_s))
                    except Exception:
                        pass
            canonical = page.locator('link[rel="canonical"]')
            canonical_url = validate_threads_url((canonical.get_attribute("href") if canonical.count() else None) or page.url)
        finally:
            ctx.close()
            if not use_persistent:
                browser.close()

    posts = _collect_post_objects(captured_payloads)
    if not posts and dom_fallback:
        posts = dom_fallback

    if not posts:
        raise RuntimeError("Không đọc được nội dung bài viết Threads. Hãy kiểm tra link hoặc bấm Đăng nhập Threads.")

    match = re.search(r"/(?:post|t)/([A-Za-z0-9_-]+)", canonical_url)
    root = next((post for post in [*posts, *dom_fallback] if match and post.get("shortcode") == match.group(1)), None)
    if root is None:
        raise RuntimeError("Không xác định được bài gốc theo URL/shortcode; không dùng bài đầu tiên thay thế.")
    if cancelled():
        raise RuntimeError("Đã dừng lấy bình luận.")
    root_id = root.get("source_post_id") or root["shortcode"]
    root["source_post_id"] = root_id
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for post in posts:
        if post.get("parent_post_id"):
            by_parent.setdefault(post["parent_post_id"], []).append(post)
    replies: list[dict[str, Any]] = []
    pending = deque([root_id])
    seen = {root_id}
    while pending:
        for reply in by_parent.get(pending.popleft(), []):
            post_id = reply["source_post_id"]
            if post_id and post_id not in seen:
                seen.add(post_id)
                replies.append(reply)
                pending.append(post_id)
    extraction = "json"
    if not replies:
        extraction = "dom"
        seen_codes = {root["shortcode"]}
        for post in dom_fallback:
            code = post.get("shortcode", "")
            if code and code not in seen_codes:
                seen_codes.add(code)
                replies.append(dict(post, source_post_id=post.get("source_post_id") or code))
    pool = [dict(root, seg_id="root"), *(dict(item, seg_id=f"cmt_{idx:02d}") for idx, item in enumerate(replies, 1))]
    if candidates is not None:
        candidates[:] = pool
    if coverage is not None:
        coverage.clear()
        coverage.update(source="playwright", browser="edge", extraction=extraction,
                        scroll_count=10, fetched=len(replies), scope="loaded_replies")
    return select_thread_segments(pool, media_cache_dir, comment_mode, comment_sort, max_comments)


def select_thread_segments(
    candidates: list[dict[str, Any]], media_cache_dir: Path,
    comment_mode: str, comment_sort: str, max_comments: int,
) -> tuple[str, list[SegmentItem]]:
    """Select from the cached pool without opening Threads again or downloading unused media."""
    root = candidates[0]
    filtered = _select_comments(root, candidates[1:], comment_mode=comment_mode, max_comments=max_comments, comment_sort=comment_sort)
    all_items = [root, *filtered]
    media_cache_dir.mkdir(parents=True, exist_ok=True)
    segments: list[SegmentItem] = []
    for idx, item in enumerate(all_items):
        seg_id = item["seg_id"]
        avatar_local = _download_asset(item.get("avatar_url", ""), media_cache_dir, f"{seg_id}_avatar")
        img_locals: list[str] = []
        for img_i, img_url in enumerate(item.get("image_urls", [])[:2]):
            local_p = _download_asset(img_url, media_cache_dir, f"{seg_id}_img_{img_i}")
            if local_p:
                img_locals.append(local_p)

        segments.append(
            SegmentItem(
                seg_id=seg_id,
                is_root_post=(idx == 0),
                username=item.get("username", "threads_user"),
                avatar_url=item.get("avatar_url", ""),
                avatar_local=avatar_local,
                raw_text=item.get("text", "").strip(),
                spoken_text=item.get("text", "").strip(),
                image_urls=item.get("image_urls", []),
                image_locals=img_locals,
                likes=optional_count(item.get("likes")),
                replies=optional_count(item.get("replies")),
                reposts=optional_count(item.get("reposts")),
                quotes=optional_count(item.get("quotes")),
                source_post_id=item.get("source_post_id", ""),
                parent_post_id=item.get("parent_post_id", ""),
                timestamp=item.get("timestamp", ""),
            )
        )

    slug = _make_slug(root.get("text", "") or root.get("username", "threads"))
    return slug, segments


def parse_manual_script(raw_script: str) -> tuple[str, list[SegmentItem]]:
    """Turn user-entered blocks (separated by blank lines or `---`) into SegmentItems."""
    blocks = [b.strip() for b in re.split(r"\n\s*---+\s*\n|\n\s*\n", raw_script.strip()) if b.strip()]
    if not blocks:
        raise ValueError("Nội dung kịch bản trống.")

    segments: list[SegmentItem] = []
    for idx, blk in enumerate(blocks):
        username = "tac_gia_threads" if idx == 0 else f"nguoi_dung_{idx:02d}"
        likes = max(50, 2400 // (idx + 1))
        text = blk
        # Support optional `@username: content` prefix
        m = re.match(r"^@?([a-zA-Z0-9._]{2,30})\s*\|\s*(\d+)\s*:\s*(.+)$", blk, re.DOTALL)
        if m:
            username, likes_s, text = m.group(1), m.group(2), m.group(3).strip()
            likes = int(likes_s)
        else:
            m2 = re.match(r"^@([a-zA-Z0-9._]{2,30})\s*:\s*(.+)$", blk, re.DOTALL)
            if m2:
                username, text = m2.group(1), m2.group(2).strip()

        segments.append(
            SegmentItem(
                seg_id="root" if idx == 0 else f"cmt_{idx:02d}",
                is_root_post=(idx == 0),
                username=username,
                raw_text=text,
                spoken_text=text,
                likes=likes,
                replies=max(2, likes // 35),
                reposts=max(1, likes // 18),
            )
        )
    return _make_slug(segments[0].raw_text), segments


def sample_video1_script() -> str:
    """Exact viral Vietnamese words thread from Video 1 for instant 1-click benchmarking."""
    return (
        '@yumemikawa | 7800: Có ai thích từ “nức nở” trong tiếng Việt giống mình không. Đối với mình đây là từ mình thích nhất. '
        "Nó rất đặc biệt và mình ko tìm đc bất cứ từ nước ngoài nào cho mình cảm giác giống nó hết\n\n"
        '@threednatam_ | 1100: Từ tiếng Việt mình thích nhất là chữ “thương”. Trong tiếng Anh dù từ nào đi nữa nó cũng không trọn gói được cái tình và cái ý của chữ “thương”.\n\n'
        '@griffin.jinbe.67 | 1000: với t thì là từ “thổn thức”, nó diễn tả cảm xúc dâng trào, gần như nức nở nhưng lại lặng im trong lòng.\n\n'
        '@putimain | 565: tui thích từ dỗi nữa =)))) kiểu chẳng tìm được cái từ nào ở nc bạn mang cái nghĩa nũng nịu nnay\n\n'
        '@motchaucay | 410: tôi lại ấn tượng với từ “lả lơi” 😍 nói chung khả năng biểu đạt của tiếng Việt quá đỉnh, chỉ một từ ngữ nhỏ bé, khi đọc lên đã gợi bao nhiêu hình dung\n\n'
        '@mem_tra_can | 233: của tui là “thanh” tui có cảm giác nó sạch mà nó mát vl :)))'
    )


def _collect_post_objects(payloads: list[Any]) -> list[dict[str, Any]]:
    seen_pks: set[str] = set()
    extracted: list[dict[str, Any]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if "post" in node and isinstance(node["post"], dict):
                _try_parse_post(node["post"])
            elif "user" in node and ("caption" in node or "text_post_app_info" in node):
                _try_parse_post(node)
            for key, value in node.items():
                if key not in {"relatedPosts", "related_posts"}:
                    _walk(value)
        elif isinstance(node, list):
            for elem in node:
                _walk(elem)

    def _try_parse_post(p: dict[str, Any]) -> None:
        pk = str(p.get("pk") or p.get("id") or "")
        user = p.get("user") or {}
        username = user.get("username") or ""
        caption = p.get("caption") or {}
        text = caption.get("text") if isinstance(caption, dict) else ""
        if not text:
            # Try text_fragments
            frags = (((p.get("text_post_app_info") or {}).get("text_fragments") or {}).get("fragments") or [])
            text = "".join(f.get("plaintext", "") for f in frags if isinstance(f, dict))
        text = (text or "").strip()
        images = _extract_post_images(p)
        if not username or (not text and not images):
            return
        dedup_key = pk or f"{username}:{text[:50]}"
        if dedup_key in seen_pks:
            return
        seen_pks.add(dedup_key)

        info = p.get("text_post_app_info") or {}
        timestamp = ""
        if p.get("taken_at") is not None:
            try:
                timestamp = datetime.fromtimestamp(float(p["taken_at"]), tz=timezone.utc).isoformat()
            except (TypeError, ValueError, OverflowError, OSError):
                pass
        extracted.append(
            {
                "source_post_id": pk.split("_", 1)[0],
                "parent_post_id": str(info.get("reply_to_post_id") or "").split("_", 1)[0],
                "timestamp": timestamp,
                "shortcode": p.get("code") or p.get("shortcode") or "",
                "username": username,
                "avatar_url": user.get("profile_pic_url") or "",
                "text": text,
                "image_urls": images,
                "likes": optional_count(p.get("like_count")),
                "replies": optional_count(info.get("direct_reply_count")),
                "reposts": optional_count(info.get("repost_count")),
                "quotes": optional_count(info.get("quote_count")),
            }
        )

    for payload in payloads:
        _walk(payload)
    return extracted


def _extract_post_images(p: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    carousel = p.get("carousel_media") or []
    candidates_containers = carousel if carousel else [p]
    for item in candidates_containers:
        if not isinstance(item, dict):
            continue
        # Skip video thumbnails if video_versions exist? Still useful if post is image meme
        img_v2 = (item.get("image_versions2") or {}).get("candidates") or []
        if img_v2 and isinstance(img_v2[0], dict) and img_v2[0].get("url"):
            if not item.get("video_versions"):
                urls.append(img_v2[0]["url"])
    return urls


def _extract_dom_fallback(page) -> list[dict[str, Any]]:
    try:
        return page.evaluate(
            """() => {
                const results = [];
                const related = Array.from(document.querySelectorAll('h1,h2,h3,span,[role="heading"]'))
                    .find(el => /^(Thread liên quan|Bài viết liên quan|Related threads|Related posts)$/i.test(el.textContent.trim()));
                const parseCount = (text) => {
                    const value = text.trim().replace(/\\s/g, '');
                    if (!/^[0-9][0-9.,]*[KMB]?$/i.test(value)) return null;
                    const unit = value.slice(-1).toUpperCase();
                    if ('KMB'.includes(unit)) {
                        return Math.round(parseFloat(value.slice(0, -1).replace(',', '.')) * ({K:1000,M:1000000,B:1000000000}[unit]));
                    }
                    return Number(value.replace(/[.,]/g, ''));
                };
                const articles = document.querySelectorAll('[data-pressable-container="true"]');
                articles.forEach((el) => {
                    if (related && (el.contains(related) || (el.compareDocumentPosition(related) & Node.DOCUMENT_POSITION_PRECEDING))) return;
                    const userLink = el.querySelector('a[href^="/@"]');
                    if (!userLink) return;
                    const username = userLink.getAttribute('href').replace('/@', '').split('/')[0];
                    const avatarImg = el.querySelector('img[alt*="profile"], img');
                    const spans = Array.from(el.querySelectorAll('span[dir="auto"]'))
                        .map(s => s.innerText.trim())
                        .filter(t => t && t !== username && !/^[0-9.,KMB]+$/.test(t) && t.length > 2);
                    const text = spans.join('\\n').trim();
                    const postLink = el.querySelector('a[href*="/post/"]');
                    const code = postLink?.getAttribute('href')?.match(/\\/post\\/([A-Za-z0-9_-]+)/)?.[1] || '';
                    if (username && text) {
                        const counts = {likes:null, replies:null, reposts:null, quotes:null};
                        el.querySelectorAll('svg[aria-label]').forEach(icon => {
                            const label = icon.getAttribute('aria-label') || '';
                            const button = icon.closest('button,[role="button"]');
                            const value = button ? parseCount(button.innerText) : null;
                            if (/thích|like/i.test(label)) counts.likes = value;
                            else if (/trả lời|bình luận|repl/i.test(label)) counts.replies = value;
                            else if (/đăng lại|repost/i.test(label)) counts.reposts = value;
                            else if (/trích dẫn|quote/i.test(label)) counts.quotes = value;
                        });
                        results.push({
                            username,
                            shortcode: code,
                            avatar_url: avatarImg ? avatarImg.src : '',
                            text,
                            image_urls: [],
                            ...counts
                        });
                    }
                });
                const canonical = document.querySelector('link[rel="canonical"]')?.href || location.href;
                const rootCode = canonical.match(/\\/(?:post|t)\\/([A-Za-z0-9_-]+)/)?.[1];
                const first = results.findIndex(item => item.shortcode === rootCode);
                return first >= 0 ? results.slice(first) : [];
            }"""
        )
    except Exception:
        return []


def _select_comments(
    root: dict[str, Any],
    replies: list[dict[str, Any]],
    *,
    comment_mode: str,
    max_comments: int,
    comment_sort: str = "likes",
) -> list[dict[str, Any]]:
    author = root.get("username", "")
    clean: list[dict[str, Any]] = []
    for r in replies:
        txt = r.get("text", "")
        if txt and r.get("username") != author and is_spam_comment(txt):
            continue
        if not txt and not r.get("image_urls"):
            continue
        clean.append(r)

    if comment_mode == CommentMode.AUTHOR_ONLY.value:
        # Keep chronological order for multi-part author storytelling!
        author_items = [r for r in clean if r.get("username") == author]
        author_items.sort(key=lambda item: (not bool(item.get("timestamp")), item.get("timestamp", "")))
        return author_items[:max_comments]

    if comment_mode == CommentMode.TOP_LIKES_NO_AUTHOR.value:
        clean = [r for r in clean if r.get("username") != author]

    if comment_sort not in {"likes", "replies", "reposts", "quotes"}:
        raise ValueError("Tiêu chí sắp xếp bình luận không hợp lệ.")
    clean.sort(key=lambda item: (item.get(comment_sort) is not None, item.get(comment_sort) or 0), reverse=True)
    return clean[:max_comments]


def _download_asset(url: str, cache_dir: Path, prefix: str) -> str:
    if not url or not url.startswith("http"):
        return ""
    ext = ".png" if ".png" in url.lower() else ".jpg"
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
    dest = cache_dir / f"{prefix}_{digest}{ext}"
    if dest.exists() and dest.stat().st_size > 100:
        return str(dest)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            dest.write_bytes(resp.read())
        return str(dest)
    except Exception:
        return ""


def _make_slug(text: str) -> str:
    words = re.findall(r"[a-zA-Z0-9à-ỹÀ-ỸđĐ]+", text.lower())[:4]
    if not words:
        return "threads_video"
    raw = "_".join(words)
    # Transliterate Vietnamese accents for clean MP4 filenames (like giamsuc.mp4 in Video 2)
    vi_map = str.maketrans(
        "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ",
        "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd",
    )
    slug = re.sub(r"[^a-z0-9_]", "", raw.translate(vi_map))
    return slug[:32] or "threads_video"

