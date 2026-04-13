from datetime import datetime, timezone

from gazzeton.config import Config
from gazzeton.fetcher import Article


def _relative_time(dt: datetime) -> str:
    """Format a datetime as a human-readable relative time."""
    now = datetime.now(timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        m = seconds // 60
        return f"{m}m ago"
    if seconds < 86400:
        h = seconds // 3600
        return f"{h}h ago"
    d = seconds // 86400
    return f"{d}d ago"


def _truncate(text: str, length: int = 200) -> str:
    if len(text) <= length:
        return text
    return text[:length].rstrip() + "..."


def format_markdown(
    results: dict[str, list[Article]],
    errors: list[str],
    config: Config,
    hours: int,
) -> str:
    """Render fetched articles as Markdown."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Gazzeton - {now.strftime('%Y-%m-%d')}",
        "",
        f"*Generated {date_str} | Last {hours}h window*",
        "",
    ]

    total_articles = 0

    # Preserve category order from config
    for cat in config.categories:
        articles = results.get(cat.name, [])
        if not articles:
            continue

        lines.append(f"## {cat.name}")
        lines.append("")

        # Group by source within category
        by_source: dict[str, list[Article]] = {}
        for a in articles:
            by_source.setdefault(a.source, []).append(a)

        for source_name, source_articles in by_source.items():
            lines.append(f"### {source_name}")
            lines.append("")
            for a in source_articles:
                total_articles += 1
                rel = _relative_time(a.published)
                lines.append(f"- [{a.title}]({a.url}) — *{rel}*")
                if a.description:
                    desc = _truncate(a.description)
                    lines.append(f"  > {desc}")
                lines.append("")

    if not total_articles:
        lines.append("*No new articles found in this time window.*")
        lines.append("")

    # Stats footer
    total_feeds = sum(len(cat.feeds) for cat in config.categories)
    lines.append("---")
    lines.append("")
    lines.append(f"**{total_articles}** articles from **{total_feeds}** feeds checked")
    if errors:
        lines.append(f"  | **{len(errors)}** feeds had errors")
    lines.append("")

    if errors:
        lines.append("<details><summary>Feed errors</summary>")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)
