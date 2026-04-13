from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
import sys

import click
import feedparser

from gazzeton.config import Category, Config
from gazzeton.discover import discover_feed


@dataclass
class Article:
    title: str
    url: str
    published: datetime
    source: str
    description: str


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


def _parse_date(entry) -> datetime | None:
    """Try to extract a timezone-aware datetime from a feed entry."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, field, None)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

    for field in ("published", "updated"):
        raw = getattr(entry, field, None)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except (ValueError, TypeError):
                continue

    return None


def fetch_feed(
    url: str,
    source_name: str,
    cutoff: datetime,
    max_articles: int,
    timeout: int,
) -> tuple[list[Article], str | None]:
    """Fetch and parse a single RSS feed. Returns (articles, error_or_None)."""
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Gazzeton/0.1"})

        if feed.bozo and not feed.entries:
            return [], f"Parse error: {feed.bozo_exception}"

        articles = []
        for entry in feed.entries:
            pub = _parse_date(entry)
            if pub is None:
                continue
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub < cutoff:
                continue

            title = entry.get("title", "Untitled")
            link = entry.get("link", "")
            desc = _strip_html(entry.get("summary", entry.get("description", "")))

            articles.append(Article(
                title=title,
                url=link,
                published=pub,
                source=source_name,
                description=desc,
            ))

        articles.sort(key=lambda a: a.published, reverse=True)
        return articles[:max_articles], None

    except Exception as e:
        return [], str(e)


def _resolve_feed_url(url: str, source_name: str, rsshub_base: str, timeout: int) -> tuple[str, str | None]:
    """Resolve a URL to its RSS feed URL. Returns (feed_url, error_or_None)."""
    try:
        resolved = discover_feed(url, rsshub_base=rsshub_base, timeout=timeout)
        if resolved != url:
            click.echo(f"  Discovered feed for {source_name}: {resolved}", err=True)
        return resolved, None
    except Exception as e:
        return url, f"Discovery failed: {e}"


def fetch_all(config: Config, hours: int | None = None) -> tuple[dict[str, list[Article]], list[str]]:
    """Fetch all feeds in parallel. Returns (category->articles, errors)."""
    h = hours if hours is not None else config.settings.hours
    now = datetime.now(timezone.utc)
    default_cutoff = now - timedelta(hours=h)
    rsshub_base = config.settings.rsshub_url

    results: dict[str, list[Article]] = {}
    errors: list[str] = []

    # Phase 1: Resolve all URLs (discover RSS feeds from website URLs)
    tasks = []
    for cat in config.categories:
        for feed in cat.feeds:
            tasks.append((cat.name, feed))

    resolved: list[tuple[str, str, str, datetime]] = []  # (cat_name, feed_name, feed_url, cutoff)
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {}
        for cat_name, feed in tasks:
            fut = pool.submit(
                _resolve_feed_url,
                feed.url,
                feed.name,
                rsshub_base,
                config.settings.fetch_timeout,
            )
            futures[fut] = (cat_name, feed)

        for fut in as_completed(futures):
            cat_name, feed = futures[fut]
            # Use per-feed hours if set, otherwise the global default
            feed_cutoff = now - timedelta(hours=feed.hours) if feed.hours else default_cutoff
            try:
                feed_url, err = fut.result(timeout=config.settings.fetch_timeout + 5)
                if err:
                    errors.append(f"[{feed.name}] {err}")
                resolved.append((cat_name, feed.name, feed_url, feed_cutoff))
            except Exception as e:
                errors.append(f"[{feed.name}] Discovery timeout: {e}")
                resolved.append((cat_name, feed.name, feed.url, feed_cutoff))

    # Phase 2: Fetch all resolved feeds
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {}
        for cat_name, feed_name, feed_url, feed_cutoff in resolved:
            fut = pool.submit(
                fetch_feed,
                feed_url,
                feed_name,
                feed_cutoff,
                config.settings.max_articles_per_feed,
                config.settings.fetch_timeout,
            )
            futures[fut] = (cat_name, feed_name, feed_url)

        for fut in as_completed(futures):
            cat_name, feed_name, feed_url = futures[fut]
            try:
                articles, err = fut.result(timeout=config.settings.fetch_timeout + 5)
                if err:
                    errors.append(f"[{feed_name}] {err}")
                if articles:
                    results.setdefault(cat_name, []).extend(articles)
            except Exception as e:
                errors.append(f"[{feed_name}] {e}")

    # Sort each category's articles newest-first
    for cat_name in results:
        results[cat_name].sort(key=lambda a: a.published, reverse=True)

    return results, errors
