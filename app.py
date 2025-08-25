import os, re, json, hashlib, argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import requests, feedparser
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("output")
DATA_DIR = OUTPUT_DIR / "data"
STATIC_DIR = OUTPUT_DIR / "static"
for p in [OUTPUT_DIR, DATA_DIR, STATIC_DIR]:
    p.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / ".nojekyll").write_text("")

def now_utc():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def log(msg):
    ts = now_utc()
    print(f"[{ts}] {msg}")
    with open(DATA_DIR / "logs.txt", "a", encoding="utf-8") as fh:
        fh.write(f"[{ts}] {msg}\n")

def truncate_html(text, n=360):
    if not text: return ""
    t = re.sub("<.*?>", "", text)
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "..."

HEADERS = {"User-Agent": "Mozilla/5.0 Universal-Health-Agent/1.0"}

def get_og_image(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10); r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        for css, attr in [
            ('meta[property="og:image"]', "content"),
            ('meta[name="twitter:image"]', "content"),
        ]:
            tag = soup.select_one(css)
            if tag and tag.get(attr):
                return tag.get(attr)
    except Exception:
        return None
    return None

BASE_FEEDS = [
    ("NIH", "https://www.nih.gov/news-events/news-releases/rss.xml"),
    ("WHO", "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml"),
    ("Nature", "https://www.nature.com/nature.rss"),
    ("BMJ", "https://www.bmj.com/latest.xml"),
    ("Lancet", "https://www.thelancet.com/rssfeed/lancet_current.xml"),
]

def fetch_feed(source, url, limit=50):
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        fp = feedparser.parse(resp.content)
        for e in fp.entries[:limit]:
            items.append({
                "source": source,
                "title": e.get("title", "").strip(),
                "link": e.get("link", "").strip(),
                "summary": truncate_html(e.get("summary", "") or e.get("description", "")),
                "date": e.get("published", ""),
                "image": None
            })
    except Exception as ex:
        log(f"Error fetching {source}: {ex}")
    return items

def aggregate(query):
    feeds = BASE_FEEDS[:]
    if query:
        feeds.insert(0, ("Google News", f"https://news.google.com/rss/search?q={requests.utils.quote(query)}"))
    items = []
    for src, url in feeds:
        items.extend(fetch_feed(src, url))
    for it in items[:100]:
        it["image"] = get_og_image(it["link"])
    return items

def build(query):
    items = aggregate(query)
    (DATA_DIR / "items.json").write_text(json.dumps(items, indent=2))
    (DATA_DIR / "logs.txt").write_text(f"Generated {len(items)} items at {now_utc()}\\n")
    print(f"✅ {len(items)} items built")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="longevity therapy OR chronic disease treatment")
    args = ap.parse_args()
    build(args.query)
