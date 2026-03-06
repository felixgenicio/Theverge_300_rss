#!/usr/bin/env python3
"""
fetch_verge.py - Fetches The Verge RSS and maintains a local RSS file with up to 300 entries.
Run every 10 minutes via cron or systemd timer.
"""

import json
import logging
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, format_datetime

VERGE_RSS_URL = "https://www.theverge.com/rss/index.xml"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STORE_FILE = os.path.join(SCRIPT_DIR, "entries.json")
OUTPUT_RSS = os.path.join(SCRIPT_DIR, "verge.rss")
MAX_ENTRIES = 300
USER_AGENT = "Mozilla/5.0 (compatible; verge-rss-aggregator/1.0)"
# URL where verge.rss will be served (used in the feed's atom:link self reference).
# Override via environment variable OUTPUT_RSS_URL if needed.
OUTPUT_RSS_URL = os.environ.get("OUTPUT_RSS_URL", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, "fetch_verge.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def fetch_feed(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def parse_atom(data: bytes) -> list[dict]:
    """Parse Atom feed (The Verge uses Atom format)."""
    NS = {
        "atom": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
    }

    def text(element, tag):
        el = element.find(tag, NS)
        return el.text if el is not None and el.text else ""

    def attr(element, tag, attribute):
        el = element.find(tag, NS)
        return el.get(attribute, "") if el is not None else ""

    root = ET.fromstring(data)
    entries = []
    for entry in root.findall("atom:entry", NS):
        link = attr(entry, "atom:link[@rel='alternate']", "href") or attr(entry, "atom:link", "href")
        guid = text(entry, "atom:id") or link
        title = text(entry, "atom:title")
        summary = text(entry, "atom:summary") or text(entry, "atom:content")
        published = text(entry, "atom:published") or text(entry, "atom:updated")
        author = text(entry, "atom:author/atom:name")

        # Normalise published to RFC-2822 for RSS compatibility
        pub_dt = None
        if published:
            try:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                pass

        entries.append({
            "guid": guid,
            "title": title,
            "link": link,
            "summary": summary,
            "published": pub_dt.isoformat() if pub_dt else published,
            "author": author,
        })
    return entries


def parse_rss(data: bytes) -> list[dict]:
    """Parse RSS 2.0 feed as fallback."""
    def text(element, tag):
        el = element.find(tag)
        return el.text if el is not None and el.text else ""

    root = ET.fromstring(data)
    channel = root.find("channel")
    if channel is None:
        return []
    entries = []
    for item in channel.findall("item"):
        guid = text(item, "guid") or text(item, "link")
        published = text(item, "pubDate")
        pub_dt = None
        if published:
            try:
                pub_dt = parsedate_to_datetime(published)
            except Exception:
                pass

        entries.append({
            "guid": guid,
            "title": text(item, "title"),
            "link": text(item, "link"),
            "summary": text(item, "description"),
            "published": pub_dt.isoformat() if pub_dt else published,
            "author": text(item, "author") or text(item, "dc:creator"),
        })
    return entries


def load_store() -> dict[str, dict]:
    if not os.path.exists(STORE_FILE):
        return {}
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Could not read store file (%s), starting fresh: %s", STORE_FILE, e)
        return {}


def save_store(store: dict[str, dict]):
    tmp_file = STORE_FILE + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, STORE_FILE)
    except OSError as e:
        log.error("Failed to save store file: %s", e)
        raise


def entry_datetime(entry: dict) -> datetime:
    pub = entry.get("published", "")
    try:
        return datetime.fromisoformat(pub)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )


def pub_date_rss(entry: dict) -> str:
    try:
        dt = datetime.fromisoformat(entry["published"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return format_datetime(dt)
    except Exception:
        return entry.get("published", "")


def generate_rss(entries: list[dict]) -> str:
    now_rfc = format_datetime(datetime.now(timezone.utc))
    items = []
    for e in entries:
        title = escape_xml(e.get("title") or "")
        link = e.get("link") or ""
        guid = escape_xml(e.get("guid") or link)
        summary = e.get("summary") or ""
        author = escape_xml(e.get("author") or "")
        pub = pub_date_rss(e)

        item = f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{pub}</pubDate>
      <author>{author}</author>
      <description><![CDATA[{summary}]]></description>
    </item>"""
        items.append(item)

    items_xml = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>The Verge (aggregated)</title>
    <link>https://www.theverge.com</link>
    <description>The Verge - last {len(entries)} entries (locally aggregated)</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <atom:link href="{OUTPUT_RSS_URL}" rel="self" type="application/rss+xml"/>
{items_xml}
  </channel>
</rss>
"""


def main():
    log.info("Fetching %s", VERGE_RSS_URL)
    try:
        data = fetch_feed(VERGE_RSS_URL)
    except Exception as e:
        log.error("Failed to fetch feed: %s", e)
        sys.exit(1)

    # Detect format and parse
    try:
        if b"<feed" in data[:500]:
            new_entries = parse_atom(data)
        else:
            new_entries = parse_rss(data)
        log.info("Parsed %d entries from feed", len(new_entries))
    except Exception as e:
        log.error("Failed to parse feed: %s", e)
        sys.exit(1)

    # Merge with stored entries
    store = load_store()
    for entry in new_entries:
        guid = entry["guid"]
        if guid and guid not in store:
            store[guid] = entry

    # Sort by date descending, keep MAX_ENTRIES
    all_entries = sorted(store.values(), key=entry_datetime, reverse=True)
    kept = all_entries[:MAX_ENTRIES]

    # Trim store to MAX_ENTRIES to avoid unbounded growth
    store = {e["guid"]: e for e in kept if e.get("guid")}
    save_store(store)
    log.info("Store now has %d entries", len(store))

    # Write RSS output
    rss_content = generate_rss(kept)
    with open(OUTPUT_RSS, "w", encoding="utf-8") as f:
        f.write(rss_content)
    log.info("Written %s with %d items", OUTPUT_RSS, len(kept))


if __name__ == "__main__":
    main()
