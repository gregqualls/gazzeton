from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Feed:
    name: str
    url: str
    hours: int | None = None  # Per-feed time window override


@dataclass
class Category:
    name: str
    feeds: list[Feed]


@dataclass
class Settings:
    hours: int = 24
    output_dir: str = "./output"
    max_articles_per_feed: int = 20
    fetch_timeout: int = 10
    rsshub_url: str = "https://rsshub.app"


@dataclass
class Config:
    settings: Settings
    categories: list[Category]


def load_config(path: Path) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)

    raw_settings = raw.get("settings", {})
    settings = Settings(**raw_settings)

    categories = []
    for cat in raw.get("categories", []):
        feeds = [Feed(**f) for f in cat.get("feeds", [])]
        categories.append(Category(name=cat["name"], feeds=feeds))

    return Config(settings=settings, categories=categories)
