"""Discover RSS feed URLs from regular website URLs and social media profiles."""

import re
import urllib.request
import urllib.error
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse


# Known RSS bridge for Twitter/X
DEFAULT_RSSHUB = "https://rsshub.app"

# Common RSS paths to try if <link> discovery fails
COMMON_FEED_PATHS = [
    "/feed/",
    "/feed",
    "/rss",
    "/rss/",
    "/rss.xml",
    "/feed.xml",
    "/atom.xml",
    "/index.xml",
    "/feeds/posts/default",
    "/?feed=rss2",
]


class _FeedLinkParser(HTMLParser):
    """Extract <link rel="alternate"> feed URLs from HTML <head>."""

    def __init__(self):
        super().__init__()
        self.feeds: list[dict[str, str]] = []
        self._in_head = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag == "head":
            self._in_head = True
            return
        if tag == "body":
            self._in_head = False
            return

        if tag != "link" or not self._in_head:
            return

        attr_dict = {k: v for k, v in attrs if v is not None}
        rel = attr_dict.get("rel", "")
        feed_type = attr_dict.get("type", "")
        href = attr_dict.get("href", "")

        if "alternate" in rel and href and feed_type in (
            "application/rss+xml",
            "application/atom+xml",
            "application/feed+json",
            "application/xml",
            "text/xml",
        ):
            self.feeds.append({
                "url": href,
                "type": feed_type,
                "title": attr_dict.get("title", ""),
            })


def _is_feed_url(url: str) -> bool:
    """Heuristic: does this URL look like it's already an RSS/Atom feed?"""
    path = urlparse(url).path.lower()
    feed_extensions = (".xml", ".rss", ".atom", ".json")
    feed_segments = ("/feed", "/rss", "/atom")

    if any(path.endswith(ext) for ext in feed_extensions):
        return True
    if any(seg in path for seg in feed_segments):
        return True
    return False


def _is_twitter_url(url: str) -> bool:
    """Check if URL is a Twitter/X profile."""
    host = urlparse(url).hostname or ""
    return host in ("twitter.com", "www.twitter.com", "x.com", "www.x.com")


def _twitter_to_rss(url: str, rsshub_base: str) -> str:
    """Convert a Twitter/X profile URL to an RSSHub feed URL."""
    path = urlparse(url).path.strip("/")
    # Handle urls like twitter.com/username or twitter.com/username/status/...
    username = path.split("/")[0]
    if not username:
        raise ValueError(f"Could not extract Twitter username from: {url}")
    return f"{rsshub_base}/twitter/user/{username}"


def _fetch_html(url: str, timeout: int = 10) -> str:
    """Fetch HTML content from a URL."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Gazzeton/0.1 (RSS Feed Discovery)",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _probe_feed(url: str, timeout: int = 10) -> bool:
    """Check if a URL returns valid RSS/Atom content."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Gazzeton/0.1 (RSS Feed Discovery)",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            # Check content type
            if any(t in content_type for t in ("xml", "rss", "atom")):
                return True
            # If content type is ambiguous, check first bytes
            start = resp.read(500).decode("utf-8", errors="replace").strip()
            return start.startswith("<?xml") or "<rss" in start or "<feed" in start
    except Exception:
        return False


def discover_feed(url: str, rsshub_base: str = DEFAULT_RSSHUB, timeout: int = 10) -> str:
    """
    Given any URL, return the best RSS/Atom feed URL.

    Handles:
    1. Already an RSS URL -> return as-is
    2. Twitter/X URL -> convert via RSSHub
    3. Regular website -> discover via <link> tags in HTML, then try common paths
    """
    url = url.strip()

    # Twitter/X special handling
    if _is_twitter_url(url):
        return _twitter_to_rss(url, rsshub_base)

    # Already looks like a feed URL
    if _is_feed_url(url):
        return url

    # Try HTML <link> discovery
    try:
        html = _fetch_html(url, timeout)
        parser = _FeedLinkParser()
        parser.feed(html)

        if parser.feeds:
            # Prefer RSS over Atom, take the first
            rss_feeds = [f for f in parser.feeds if "rss" in f["type"]]
            best = rss_feeds[0] if rss_feeds else parser.feeds[0]
            return urljoin(url, best["url"])
    except Exception:
        pass

    # Fallback: probe common feed paths
    base = url.rstrip("/")
    for path in COMMON_FEED_PATHS:
        candidate = base + path
        if _probe_feed(candidate, timeout):
            return candidate

    # Nothing found - return original URL and let feedparser try it
    return url
