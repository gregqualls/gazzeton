# Gazzeton

Deterministic RSS feed aggregator that outputs Markdown. No AI, no generative content -- just fetches, filters, and formats RSS/Atom feeds from a curated list.

> **Get started in 60 seconds:** [Copy this prompt into Claude Code](#quick-start-with-claude-code) and it'll set everything up for you -- finds your feeds, builds your config, schedules the daily task, done.

## Quick Start with Claude Code

Copy and paste this prompt into Claude Code to have it walk you through the entire setup interactively:

<details>
<summary><strong>Click to expand the setup prompt (copy button appears in top-right of code block)</strong></summary>

```
I want you to help me set up Gazzeton (https://github.com/gregqualls/gazzeton) as a daily
news aggregator on my machine. Walk me through the entire process interactively.

Here's what I need you to do, step by step:

1. CLONE & INSTALL
   - Clone the repo to a sensible location on my machine
   - Detect whether I'm on macOS, Linux, or Windows
   - Check that Python >= 3.10 is available
   - Run `pip install -e .`
   - Copy feeds.example.yaml to feeds.yaml

2. DISCOVER MY INTERESTS
   Ask me what topics and interests I want to follow. Be conversational — ask about:
   - My profession/industry (for work-relevant feeds)
   - Hobbies and personal interests
   - Specific companies, products, or people I want to track
   - Local area (city/region) for local news and events
   - Whether I want any Twitter/X accounts included
   - How much content I want (light briefing vs comprehensive)

3. BUILD MY feeds.yaml
   Based on my answers:
   - Search the web for the best RSS feeds for each topic
   - Verify each feed URL actually works by testing it with:
     python -c "import feedparser; f = feedparser.parse('URL'); print(len(f.entries), 'entries')"
   - Organise feeds into logical categories
   - Set per-feed `hours` overrides for infrequent sources (blogs: 168h, local events: 72h)
   - Write the final feeds.yaml

4. TEST RUN
   Run `python -m gazzeton --stdout --hours 48` and show me a sample of the output
   to confirm everything is working. Fix any feeds that error.

5. SCHEDULE IT
   Based on my OS:

   macOS:
   - Create a launchd plist at ~/Library/LaunchAgents/com.gazzeton.daily.plist
   - Set it to run daily at 3am (or ask me what time I prefer)
   - Output to ~/Documents/gazzeton-latest.md
   - Load it with: launchctl load ~/Library/LaunchAgents/com.gazzeton.daily.plist

   Linux:
   - Add a cron job: `0 3 * * * cd /path/to/gazzeton && python -m gazzeton -o ~/Documents/gazzeton-latest.md`

   Windows:
   - Create a run-daily.bat script
   - Create a Windows Task Scheduler task using:
     powershell.exe -Command "schtasks /create /tn 'Gazzeton Daily News' /tr 'C:\path\to\run-daily.bat' /sc daily /st 03:00 /rl limited /f"
   - Include cleanup of dated files older than 30 days

6. SET UP A COWORK SKILL (if I use Claude Cowork)
   Ask if I use Claude Cowork. If yes:
   - Create a news-briefing skill that reads ~/Documents/gazzeton-latest.md
   - The skill should curate the top stories, group by category, skip noise,
     and flag anything relevant to my work
   - Save it as a Cowork skill in the appropriate location

7. VERIFY EVERYTHING
   - Run gazzeton once to confirm the output file is created
   - Show me a summary of what was set up
   - Tell me how to manually re-run it if needed
   - Tell me how to add/remove feeds later

Start by detecting my OS and asking about my interests.
```

</details>

## Why?

AI assistants like Claude are great at summarising and curating news, but they struggle with web searches: results are inconsistent, stories repeat across runs, and sandboxed environments (like Claude Cowork) can't make outbound network requests at all.

Gazzeton solves this by running on your machine as a scheduled task. It fetches RSS feeds deterministically, writes a clean Markdown file, and your AI assistant reads that local file instead of searching the web. The result is a reliable daily news pipeline:

1. **Gazzeton** runs at 3am (or whenever), fetches all your feeds, writes `gazzeton-latest.md`
2. **Your AI assistant** reads that file and gives you a curated, summarised briefing
3. **You** get consistent, fresh, never-repeated news every morning

No API keys. No web scraping. No AI in the loop. Just RSS.

## Install

```bash
git clone https://github.com/gregqualls/gazzeton.git
cd gazzeton
pip install -e .

# Create your feed config from the example
cp feeds.example.yaml feeds.yaml
```

Edit `feeds.yaml` to add your own feeds, categories, and settings. The example comes pre-loaded with popular tech, AI, and gaming feeds to get you started.

## Usage

Run from the gazzeton project directory (where `feeds.yaml` lives):

```bash
# Default: fetch last 24h, all categories, save to ./output/gazzeton-YYYY-MM-DD.md
python -m gazzeton

# Print to stdout (useful for piping to Claude or other tools)
python -m gazzeton --stdout

# Custom time window
python -m gazzeton --hours 48

# Filter to specific categories (repeatable, case-insensitive)
python -m gazzeton --category "Warhammer" --category "Dungeons & Dragons"

# Custom output file
python -m gazzeton -o /path/to/briefing.md

# Point to a different config file
python -m gazzeton --config /path/to/feeds.yaml
```

### Options

| Flag | Description |
|------|-------------|
| `--hours N` | Time window in hours (default: 24, configurable in feeds.yaml) |
| `--category NAME` | Filter to named categories, repeatable |
| `-o, --output PATH` | Write output to a specific file |
| `--stdout` | Print Markdown to stdout |
| `--config PATH` | Path to feeds.yaml config file |

### Exit behaviour

- Status messages (feed count, article count, errors) go to **stderr**
- Markdown output goes to **stdout** (with `--stdout`) or a file
- Exit code 0 on success, 1 on config errors

## Configuration

All configuration lives in `feeds.yaml`. Edit this file to add, remove, or reorganise feeds.

### Settings

```yaml
settings:
  hours: 24                # Default time window
  output_dir: ./output     # Where output files are saved
  max_articles_per_feed: 20
  fetch_timeout: 10        # Per-feed timeout in seconds
  rsshub_url: https://rsshub.app  # RSSHub instance for Twitter/X
```

### Feed URLs

Each feed entry needs a `name` and `url`. The URL can be:

**Direct RSS/Atom feed URL** (used as-is):
```yaml
- name: xkcd
  url: https://xkcd.com/rss.xml
```

**Regular website URL** (RSS feed is auto-discovered from `<link>` tags or common paths):
```yaml
- name: Goonhammer
  url: https://www.goonhammer.com
```

**Twitter/X profile URL** (converted to RSS via RSSHub):
```yaml
- name: Anthropic
  url: https://x.com/AnthropicAI
```

### Per-feed time window

Any feed can have its own `hours` override. This is useful for feeds that post infrequently (blogs, local event sites) so you don't miss content when you skip a day or weekend:

```yaml
- name: D&D Beyond
  url: https://www.dndbeyond.com/posts.rss
  hours: 168  # look back 7 days even if global setting is 24h

- name: BBC Manchester
  url: https://feeds.bbci.co.uk/news/england/manchester/rss.xml
  hours: 72   # 3 days - catch weekend posts on Monday
```

Feeds without `hours` use the global `settings.hours` value (or the `--hours` CLI flag).

### Categories

Feeds are grouped into categories. Categories control the section headings in the output and can be filtered with `--category`.

```yaml
categories:
  - name: "AI / Machine Learning"
    feeds:
      - name: OpenAI News
        url: https://openai.com/news/rss.xml
      - name: HuggingFace Blog
        url: https://huggingface.co/blog/feed.xml

  - name: "Warhammer"
    feeds:
      - name: Goonhammer
        url: https://www.goonhammer.com
      - name: Reddit r/Warhammer40k
        url: https://www.reddit.com/r/Warhammer40k/.rss
```

## Output format

Output is a Markdown file structured by category, then by source within each category. Articles are sorted newest-first.

```markdown
# Gazzeton - 2026-04-13

*Generated 2026-04-13 07:00 UTC | Last 24h window*

## AI / Machine Learning

### OpenAI News

- [Article Title](https://example.com/article) -- *2h ago*
  > First ~200 characters of the article description...

## Warhammer

### Goonhammer

- [Another Article](https://example.com/another) -- *5h ago*
  > Description text...

---

**45** articles from **41** feeds checked
```

A stats footer shows total articles and feed count. If any feeds failed, errors are listed in a collapsible `<details>` block.

## How it works

1. Reads `feeds.yaml` for the list of categories and feed URLs
2. **Discovers** RSS feeds from any URL type (direct RSS, website, or Twitter/X)
3. **Fetches** all feeds in parallel (10 concurrent threads)
4. **Filters** articles to the configured time window (default 24h)
5. **Formats** results as Markdown grouped by category and source
6. **Writes** the output to a file and/or stdout

Deduplication is time-window based: only articles published within the last N hours are included. No persistent database is needed. Each run produces a fresh snapshot.

## Using with Claude Cowork

### Option A: Direct execution (if Claude has network access)

```
cd /path/to/gazzeton && python -m gazzeton --stdout
```

Claude reads the stdout output directly. The `--stdout` flag sends Markdown to stdout while status goes to stderr.

### Option B: Scheduled task + local file (recommended for sandboxed environments)

Since Cowork's sandbox often blocks outbound network requests, the recommended setup is:

1. Schedule gazzeton to run on your machine (cron, Task Scheduler, launchd)
2. Write the output to a known file path
3. Your Cowork skill reads that local file

**Linux/macOS cron (daily at 3am):**
```bash
0 3 * * * cd /path/to/gazzeton && python -m gazzeton -o /path/to/gazzeton-latest.md
```

**Windows Task Scheduler:**
Create a `.bat` file:
```batch
@echo off
cd /d "C:\path\to\gazzeton"
python -m gazzeton --config feeds.yaml -o "%USERPROFILE%\Documents\gazzeton-latest.md"
```

### Cowork skill template

Here's a starter skill that reads gazzeton output and generates a curated briefing. Save this as a Cowork skill and adjust the file path:

````markdown
---
description: "Daily news briefing from RSS feeds. Use when the user asks for news, a morning briefing, or 'what's happening today'."
---

# Daily News Briefing

Read the gazzeton RSS digest and produce a curated briefing for the user.

## Steps

1. Read the latest gazzeton output:
   ```
   ~/Documents/gazzeton-latest.md
   ```

2. If the file doesn't exist or is more than 36 hours old, inform the user that gazzeton hasn't run recently and suggest they run it manually:
   ```bash
   cd /path/to/gazzeton && python -m gazzeton -o ~/Documents/gazzeton-latest.md
   ```

3. From the gazzeton output, curate a briefing:
   - **Lead with the top 3-5 most significant stories** across all categories
   - Group remaining stories by category
   - For each story, write a 1-2 sentence summary (don't just copy the RSS description)
   - Skip low-signal items (job postings, listicles, routine press releases)
   - Flag anything that might require action or is directly relevant to the user's work

4. End with a quick count: "X articles reviewed across Y categories"
````

Customise the file path and curation criteria to match your setup and interests.

## Project structure

```
gazzeton/
  feeds.example.yaml    # Example config — copy to feeds.yaml to get started
  feeds.yaml            # Your personal feed config (gitignored)
  pyproject.toml        # Python package config
  LICENSE               # MIT
  src/gazzeton/
    cli.py              # CLI entry point (click)
    config.py           # YAML config loader
    discover.py         # RSS autodiscovery + Twitter/X support
    fetcher.py          # Parallel RSS fetcher with time filtering
    formatter.py        # Markdown output formatter
  output/               # Default output directory (gitignored)
```

## Adding new feeds

1. Open `feeds.yaml`
2. Add a new entry under the appropriate category (or create a new category)
3. Use any URL -- RSS feed, website, or Twitter/X profile
4. Run `python -m gazzeton --stdout --hours 48` to verify it works

## Twitter/X support

Twitter doesn't provide native RSS feeds. Gazzeton routes Twitter/X URLs through [RSSHub](https://docs.rsshub.app/), an open-source RSS bridge.

The default public instance (`https://rsshub.app`) has rate limits. If you hit them, you can [self-host RSSHub](https://docs.rsshub.app/deploy/) and update the `rsshub_url` setting in `feeds.yaml`.

## Dependencies

- Python >= 3.10
- [feedparser](https://feedparser.readthedocs.io/) -- RSS/Atom parsing
- [PyYAML](https://pyyaml.org/) -- config file
- [click](https://click.palletsprojects.com/) -- CLI
