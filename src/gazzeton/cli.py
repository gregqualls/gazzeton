import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from gazzeton.config import load_config
from gazzeton.fetcher import fetch_all
from gazzeton.formatter import format_markdown


@click.command()
@click.option("--hours", type=int, default=None, help="Time window in hours (default: from config, usually 24)")
@click.option("--category", "categories", multiple=True, help="Filter to specific categories (repeatable)")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path")
@click.option("--stdout", "to_stdout", is_flag=True, help="Print output to stdout instead of/in addition to file")
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Path to feeds.yaml")
def main(hours, categories, output, to_stdout, config_path):
    """Gazzeton - Deterministic RSS feed aggregator."""
    # Find config
    if config_path:
        cfg_path = Path(config_path)
    else:
        cfg_path = Path("feeds.yaml")
        if not cfg_path.exists():
            cfg_path = Path(__file__).parent.parent.parent / "feeds.yaml"
        if not cfg_path.exists():
            click.echo("Error: feeds.yaml not found. Use --config to specify path.", err=True)
            sys.exit(1)

    config = load_config(cfg_path)

    # Override hours
    h = hours if hours is not None else config.settings.hours

    # Filter categories if specified
    if categories:
        lower = {c.lower() for c in categories}
        config.categories = [c for c in config.categories if c.name.lower() in lower]
        if not config.categories:
            click.echo(f"Error: no matching categories found for: {', '.join(categories)}", err=True)
            sys.exit(1)

    # Fetch
    click.echo(f"Fetching {sum(len(c.feeds) for c in config.categories)} feeds (last {h}h)...", err=True)
    results, errors = fetch_all(config, h)

    total = sum(len(articles) for articles in results.values())
    click.echo(f"Found {total} articles", err=True)
    if errors:
        click.echo(f"{len(errors)} feeds had errors", err=True)

    # Format
    md = format_markdown(results, errors, config, h)

    # Output
    if to_stdout or not output:
        if to_stdout:
            click.echo(md)

    if output or not to_stdout:
        if output:
            out_path = Path(output)
        else:
            out_dir = Path(config.settings.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            out_path = out_dir / f"gazzeton-{date_str}.md"

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        click.echo(f"Written to {out_path}", err=True)


if __name__ == "__main__":
    main()
