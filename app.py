# app.py — Universal Sci & Tech Breakthrough Beat
# Builds: output/data/items.json, monthly archives (thumb+summary+NEW),
# archive index with global search, logs, and (weekly) directory catalog.
#
# Usage (GitHub Actions or local):
#   python app.py --query "longevity therapy OR chronic disease treatment evidence"
#   python app.py --query "..." --build-catalog --weekly-only
#
# Requires: requests, feedparser, beautifulsoup4, lxml

import os
import re
import json
import time
import hashlib
import argparse
import email.utils as eut
import calendar
from time import mktime
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
import feedparser
from bs4 import BeautifulSoup


# -------------------------- Paths / Setup --------------------------

OUTPUT_DIR = Path("output")
DATA_DIR = OUTPUT_DIR / "data"
STATIC_DIR = OUTPUT_DIR / "static"
ARCHIVE_DIR = OUTPUT_DIR / "archive"

for p in (OUTPUT_DIR, DATA_DIR, STATIC_DIR, ARCHIVE_DIR):
    p.mkdir(parents=True, exist_ok=True)

# Make GitHub Pages render static paths correctly
(OUTPUT_DIR / ".nojekyll").write_text("")

# Simple log file
LOG_FILE = DATA_DIR / "logs.txt"

def now_utc_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def log(msg: str) -> None:
    line = f"[{now_utc_str()}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


# -------------------------- Utils --------------------------

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<.*?>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def truncate(s: str, n: int = 360) -> str:
    s = clean_text(s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"

def normalize_key(title: str, link: str) -> str:
    host = urlparse(link or "").netloc.lower()
    t = re.sub(r"\s+", " ", (title or "").lower()).strip()
    t = re.sub(r"[^a-z0-9 ]+", "", t)
    return hashlib.sha1(f"{host}|{t}".encode()).hexdigest()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Universal-Beat/3.0; +GitHubPages Agent)"
}

def get_og_image(url: str, timeout: int = 8) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        for css, attr in [
            ('meta[property="og:image"]', "content"),
            ('meta[property="og:image:url"]', "content"),
            ('meta[name="twitter:image"]', "content"),
        ]:
            m = soup.select_one(css)
            if m and m.get(attr):
                return urljoin(url, m.get(attr).strip())
        # fallback to first non-data image
        for img in soup.find_all("img", src=True):
            src = urljoin(url, img["src"])
            if any(bad in src for bad in ("data:", "sprite", "pixel", "base64")):
                continue
            return src
    except Exception as ex:
        log(f"OG image fetch failed: {ex}")
    return None


# -------------------------- Feeds --------------------------

def google_news_feed(query: str, lang="en-IN") -> str:
    # India focus by default
    return (
        "https://news.google.com/rss/search?"
        f"q={requests.utils.quote(query)}&hl={lang}&gl=IN&ceid=IN:{lang.split('-')[0]}"
    )

def pubmed_feed(query: str) -> str:
    return (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi"
        f"?db=pubmed&term={requests.utils.quote(query)}&sort=date"
    )

BASE_FEEDS = [
    ("NIH", "https://www.nih.gov/news-events/news-releases/rss.xml"),
    ("WHO", "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml"),
    ("CDC", "https://tools.cdc.gov/api/v2/resources/media/403372.rss"),
    ("Cochrane News", "https://www.cochrane.org/news-feed.xml"),
    ("Nature", "https://www.nature.com/nature.rss"),
    ("BMJ", "https://www.bmj.com/latest.xml"),
    ("Lancet", "https://www.thelancet.com/rssfeed/lancet_current.xml"),
    ("PLOS Medicine", "https://journals.plos.org/plosmedicine/feed/atom"),
    ("ScienceDaily Health", "https://www.sciencedaily.com/rss/health_medicine.xml"),
    ("ScienceDaily Top", "https://www.sciencedaily.com/rss/top.xml"),
    ("bioRxiv Latest", "https://www.biorxiv.org/rss/latest.xml"),
    ("medRxiv Latest", "https://www.medrxiv.org/rss/latest.xml"),
]


# -------------------------- Parsing --------------------------

def parse_date(entry) -> str:
    # Try structured
    for key in ("published_parsed", "updated_parsed"):
        if entry.get(key):
            try:
                return datetime.utcfromtimestamp(mktime(entry[key])).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                pass
    # Fallback to string
    for key in ("published", "updated", "dc_date"):
        if entry.get(key):
            try:
                tt = eut.parsedate_to_datetime(entry[key])
                if tt.tzinfo:
                    tt = tt.astimezone(timezone.utc).replace(tzinfo=None)
                return tt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
    return ""


# -------------------------- Scrape & Aggregate --------------------------

def fetch_feed(source: str, url: str, limit: int, delay: float):
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        fp = feedparser.parse(resp.content)
        for e in fp.entries[:limit]:
            items.append(
                {
                    "source": source,
                    "title": (e.get("title") or "").strip(),
                    "link": (e.get("link") or "").strip(),
                    "summary": truncate(e.get("summary") or e.get("description") or ""),
                    "date": parse_date(e),
                    "image": None,
                }
            )
        log(f"Fetched {len(items)} from {source}")
    except Exception as ex:
        log(f"Fetch error from {source}: {ex}")
    finally:
        if delay > 0:
            time.sleep(delay)
    return items

def aggregate(
    query: str,
    per_feed_limit: int = 80,
    max_total: int = 700,
    thumb_budget: int = 220,
    delay_between: float = 0.4,
):
    feeds = []
    if query:
        feeds.extend(
            [
                ("Google News", google_news_feed(query)),
                ("PubMed", pubmed_feed(query)),
            ]
        )
    feeds.extend(BASE_FEEDS)

    all_items = []
    for src, url in feeds:
        all_items.extend(fetch_feed(src, url, per_feed_limit, delay_between))

    # de-dup by host+title
    seen = set()
    deduped = []
    for it in all_items:
        if not it.get("title") or not it.get("link"):
            continue
        k = normalize_key(it.get("title"), it.get("link"))
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
        if len(deduped) >= max_total:
            break

    log(f"After dedupe: {len(deduped)} items")

    # thumbnails (OG)
    for it in deduped:
        if thumb_budget <= 0:
            break
        img = get_og_image(it["link"])
        if img:
            it["image"] = img
            thumb_budget -= 1

    # newest first
    deduped.sort(key=lambda x: x.get("date") or "", reverse=True)
    return deduped


# -------------------------- Archives (with NEW badge) --------------------------

def write_archives(items):
    """Create archive pages by month with cards (image + summary) and an archive index with global search."""
    def is_new_24h(date_str: str) -> bool:
        if not date_str:
            return False
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.utcnow()
            diff = (now - dt).total_seconds()
            return 0 <= diff <= 24 * 60 * 60
        except Exception:
            return False

    def favicon_url(link: str) -> str:
        try:
            host = urlparse(link or "").hostname
            if not host:
                return ""
            return f"https://www.google.com/s2/favicons?domain={host}&sz=64"
        except Exception:
            return ""

    # Group YYYY-MM
    by_month = {}
    for it in items:
        d = (it.get("date") or "")[:10]
        ym = d[:7] if d else "unknown"
        by_month.setdefault(ym, []).append(it)

    base_css = (
        "body{font-family:system-ui,Arial;margin:20px;background:#f8f9fa;color:#212529}"
        "a{color:#0d6efd;text-decoration:none}a:hover{text-decoration:underline}"
        ".wrap{max-width:1140px;margin:0 auto}"
        ".head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}"
        "h1{margin:0 0 8px 0}"
        ".grid{display:grid;gap:14px}"
        "@media(min-width:720px){.grid{grid-template-columns:1fr 1fr}}"
        ".card{background:#fff;border:1px solid #dee2e6;border-radius:12px;overflow:hidden}"
        ".inner{display:grid;gap:12px;grid-template-columns:1fr 200px}"
        "@media(max-width:719px){.inner{grid-template-columns:1fr}}"
        ".txt{padding:14px}"
        ".thumb{width:100%;height:100%;object-fit:cover;background:#f1f3f5}"
        ".muted{color:#6c757d;font-size:.9em}"
        ".badge{display:inline-block;padding:4px 10px;border-radius:999px;font-size:.78em;margin:0 6px 6px 0;border:1px solid #dee2e6;background:#e9ecef;color:#495057}"
        ".b-new{background:#c3fae8;color:#0c5460;border-color:#96f2d7}"
        ".media{width:100%;height:100%;background:#f1f3f5;border-left:1px solid #dee2e6;display:flex;align-items:center;justify-content:center;padding:12px}"
        ".media__inner{max-height:100%;overflow:hidden;text-align:left}"
        ".media__title{font-weight:600;line-height:1.25;margin:0 0 6px 0;font-size:14px;color:#212529}"
        ".media__summary{color:#6c757d;font-size:13px;line-height:1.35}"
        ".media__row{display:flex;align-items:center;gap:8px;margin-bottom:6px}"
        ".favicon{width:16px;height:16px;border-radius:4px;background:#e9ecef;flex:0 0 auto}"
        ".searchbar{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 12px}"
        "input[type=search]{width:100%;padding:12px;border-radius:10px;border:1px solid #dee2e6;background:#fff;color:#212529}"
    )

    # Month pages
    for ym, arr in by_month.items():
        arr.sort(key=lambda x: x.get("date") or "", reverse=True)
        title = f"Archive — {ym}" if ym != "unknown" else "Archive"

        head = (
            "<!doctype html><meta charset='utf-8'><title>" + title + "</title>"
            "<style>" + base_css + "</style>"
            "<div class='wrap'>"
            f"<div class='head'><h1>{title}</h1><a href='../index.html'>← Home</a></div>"
            "<p>Items listed newest first. Each entry shows date, headline, and a short summary.</p>"
            "<div class='grid'>"
        )
        body = []
        for it in arr:
            title_txt = (it.get("title") or "").replace("<", "&lt;").replace(">", "&gt;")
            link = it.get("link") or "#"
            date_txt = it.get("date") or ""
            summary = it.get("summary") or ""
            image = it.get("image") or ""
            new_badge = "<span class='badge b-new'>NEW</span>" if is_new_24h(date_txt) else ""

            if image:
                media = f"<img class='thumb' loading='lazy' src='{image}' alt=''>"
            else:
                fav = favicon_url(link)
                icon = f"<img class='favicon' src='{fav}' alt=''>" if fav else "<span class='favicon'></span>"
                media = (
                    "<div class='media'>"
                    "<div class='media__inner'>"
                    f"<div class='media__row'>{icon}<div class='media__title'>{title_txt[:120]}</div></div>"
                    f"<div class='media__summary'>{(summary or 'No summary available.')[:180]}</div>"
                    "</div></div>"
                )

            body.append(
                "<div class='card'><div class='inner'>"
                f"<div class='txt'>{new_badge}"
                f"<h3 style='margin:.4rem 0'><a target='_blank' href='{link}'>{title_txt}</a></h3>"
                f"<div class='muted'>{date_txt}</div>"
                f"<p>{summary}</p></div>"
                f"<div>{media}</div>"
                "</div></div>"
            )

        html = head + "".join(body) + "</div></div>"
        (ARCHIVE_DIR / f"{ym}.html").write_text(html, encoding="utf-8")

    # Archive index with global search
    months = sorted(by_month.keys(), reverse=True)
    month_cards = []
    for ym in months:
        if ym == "unknown":
            name = "Unknown"
        else:
            try:
                name = datetime.strptime(ym, "%Y-%m").strftime("%B %Y")
            except Exception:
                name = ym
        month_cards.append(f"<div class='card'><div class='txt'><a href='./{ym}.html'>{name}</a></div></div>")

    idx_html = f"""<!doctype html><meta charset='utf-8'><title>Archive</title>
<style>{base_css}</style>
<div class='wrap'>
  <div class='head'><h1>Archive</h1><a href='../index.html'>← Home</a></div>
  <p>Browse by month or use the search below to find stories across all time.</p>

  <div class='searchbar'>
    <input id='q' type='search' placeholder='Search all archived stories… (title or summary)'>
  </div>
  <div id='results' class='grid'></div>

  <h2 style='margin-top:18px'>Browse by month</h2>
  <div class='grid'>
    {''.join(month_cards)}
  </div>
</div>

<script>
(async function(){{
  const box = document.getElementById('q');
  const out = document.getElementById('results');
  let all = [];
  try {{
    const r = await fetch('../data/items.json?m=' + Date.now(), {{cache:'no-store'}});
    if (r.ok) all = await r.json();
  }} catch(_){{
    // ignore
  }}

  function domain(u){{ try {{ return new URL(u).hostname; }} catch {{ return ''; }} }}
  function fav(u){{ const d = domain(u); return d ? ('https://www.google.com/s2/favicons?domain=' + encodeURIComponent(d) + '&sz=64') : ''; }}
  function isNew(dateStr){{
    if(!dateStr) return false;
    const d = new Date(dateStr.replace(' ','T') + 'Z'); // UTC
    const now = new Date();
    const diff = now - d;
    return diff >= 0 && diff <= 86400000;
  }}

  function card(i){{
    const title = i.title || '';
    const link = i.link || '#';
    const date = i.date || '';
    const summary = i.summary || '';
    const image = i.image || '';
    const newb = isNew(date) ? "<span class='badge b-new'>NEW</span>" : "";

    let media = "";
    if (image) {{
      media = "<img class='thumb' loading='lazy' src='" + image + "' alt=''>";
    }} else {{
      const f = fav(link);
      const icon = f ? ("<img class='favicon' src='" + f + "' alt=''>") : "<span class='favicon'></span>";
      media = "<div class='media'><div class='media__inner'><div class='media__row'>"
            + icon + "<div class='media__title'>" + title.slice(0,120) + "</div></div>"
            + "<div class='media__summary'>" + (summary || 'No summary available.').slice(0,180) + "</div>"
            + "</div></div>";
    }}

    return "<div class='card'><div class='inner'>"
         + "<div class='txt'>" + newb
         + "<h3 style='margin:.4rem 0'><a target='_blank' href='" + link + "'>" + title + "</a></h3>"
         + "<div class='muted'>" + date + "</div>"
         + "<p>" + summary + "</p></div>"
         + "<div>" + media + "</div>"
         + "</div></div>";
  }}

  function render(list){{ out.innerHTML = list.map(card).join(''); }}
  function refresh(){{
    const term = (box.value || '').toLowerCase();
    if (!term) {{ out.innerHTML = ''; return; }}
    const filt = all.filter(i => ((i.title||'').toLowerCase().includes(term) || (i.summary||'').toLowerCase().includes(term)));
    render(filt);
  }}

  box?.addEventListener('input', () => {{ clearTimeout(window.__t); window.__t = setTimeout(refresh, 160); }});
}})();
</script>
"""
    (ARCHIVE_DIR / "index.html").write_text(idx_html, encoding="utf-8")


# -------------------------- Logs page --------------------------

def write_logs_html():
    logs = ""
    try:
        logs = LOG_FILE.read_text(encoding="utf-8")
    except Exception:
        logs = "No logs yet."
    html = f"""<!doctype html><meta charset="utf-8"><title>Logs</title>
<style>
body{{font-family:system-ui,Arial;margin:20px;background:#f8f9fa;color:#212529}}
a{{color:#0d6efd;text-decoration:none}}a:hover{{text-decoration:underline}}
.wrap{{max-width:900px;margin:0 auto}}
pre{{white-space:pre-wrap;background:#fff;border:1px solid #dee2e6;border-radius:12px;padding:12px}}
</style>
<div class="wrap">
  <h1>Build Logs</h1>
  <p><a href="index.html">← Home</a></p>
  <pre>{logs.replace("<","&lt;").replace(">","&gt;")}</pre>
</div>
"""
    (OUTPUT_DIR / "logs.html").write_text(html, encoding="utf-8")


# -------------------------- Build (Evidence + Archives) --------------------------

def build(query: str):
    items = aggregate(query)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "items.json").write_text(json.dumps(items, indent=2), encoding="utf-8")

    # Ensure placeholders exist
    if not (DATA_DIR / "catalog.json").exists():
        (DATA_DIR / "catalog.json").write_text(
            json.dumps({"programs": [], "experts": [], "institutions": []}, indent=2),
            encoding="utf-8",
        )
    if not (DATA_DIR / "longevity_plan.json").exists():
        (DATA_DIR / "longevity_plan.json").write_text(json.dumps([], indent=2), encoding="utf-8")

    # Archives (+ cards, NEW badge) and logs page
    write_archives(items)
    LOG_FILE.write_text(
        f"Generated: {now_utc_str()}\nQuery: {query or '—'}\nItems: {len(items)}\n",
        encoding="utf-8",
    )
    write_logs_html()
    log(f"✅ Built {len(items)} items → output/data/items.json + archives + logs")


# -------------------------- Catalog (Programs/Experts/Institutions) --------------------------

def domain_of(u: str) -> str:
    try:
        return urlparse(u).netloc.lower()
    except Exception:
        return ""

def is_external_link(page_url: str, href: str) -> bool:
    if not href:
        return False
    return domain_of(page_url) != domain_of(href)

def guess_name_from_anchor(a_tag, href: str) -> str:
    txt = (a_tag.get_text(" ", strip=True) if a_tag else "")[:120]
    if txt and not txt.lower().startswith(("http://", "https://")):
        return txt
    dom = domain_of(href) or ""
    if dom.startswith("www."):
        dom = dom[4:]
    return dom or href

def make_record(kind: str, name: str, href: str, image: str | None = None, **extra):
    rec = {"name": name, "url": href, "image": image, "__type": kind}
    rec.update(extra)
    return rec

SITE_MAP = {
    "scispot_top20_longevity_biotechs": {
        "mode": "outlinks",
        "type": "institution",
        "url": "https://www.scispot.com/blog/top-20-of-most-innovative-anti-aging-companies-in-the-world",
        "container": "article, main, .blog-content, .prose",
        "tags": ["longevity", "biotech", "companies"],
    },
    "labiotech_top_biotech_companies": {
        "mode": "outlinks",
        "type": "institution",
        "url": "https://www.labiotech.eu/best-biotech/anti-aging-biotech-companies/",
        "container": "article, main, .single-content, .article__content",
        "tags": ["longevity", "biotech", "companies"],
    },
    "longevity_clinic_top18": {
        "mode": "outlinks",
        "type": "institution",
        "url": "https://longevity-clinic.co.uk/what-is-the-best-longevity-clinic-in-the-world/",
        "container": "article, main, .entry-content, .content",
        "tags": ["longevity", "clinic", "ranking"],
    },
    "lifespan_rejuvenation_roadmap": {
        "mode": "outlinks",
        "type": "program",
        "url": "https://www.lifespan.io/road-maps/the-rejuvenation-roadmap/",
        "container": "article, main, #content, .entry-content, .wrap",
        "tags": ["rejuvenation", "roadmap", "programs"],
    },
    "dr_kalidas_center": {
        "mode": "single",
        "type": "institution",
        "url": "https://drkalidas.com/",
        "name": "The Center for Natural & Integrative Medicine (Dr. Kalidas)",
        "location": "Orlando, Florida, USA",
        "tags": ["integrative", "naturopathic", "clinic"],
    },
}

def scrape_outlinks(cfg: dict):
    out = []
    try:
        page_url = cfg["url"]
        r = requests.get(page_url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        container = None
        for sel in (cfg.get("container") or "").split(","):
            node = soup.select_one(sel.strip())
            if node:
                container = node
                break
        if container is None:
            container = soup
        seen = set()
        for a in container.select("a[href]"):
            href = urljoin(page_url, a.get("href"))
            if not is_external_link(page_url, href):
                continue
            d = domain_of(href)
            if any(bad in d for bad in ("facebook.", "twitter.", "x.com", "instagram.", "linkedin.", "pinterest.", "reddit.")):
                continue
            key = (d, href.split("#")[0])
            if key in seen:
                continue
            seen.add(key)
            name = guess_name_from_anchor(a, href)
            img = get_og_image(href)
            out.append(
                make_record(
                    cfg["type"],
                    name,
                    href,
                    image=img,
                    tags=cfg.get("tags", []),
                )
            )
        log(f"[catalog] outlinks: {len(out)} from {page_url}")
    except Exception as ex:
        log(f"[catalog] outlinks error: {ex}")
    return out

def scrape_single(cfg: dict):
    out = []
    try:
        page_url = cfg["url"]
        name = cfg.get("name") or domain_of(page_url)
        img = get_og_image(page_url)
        out.append(
            make_record(
                cfg["type"],
                name,
                page_url,
                image=img,
                location=cfg.get("location"),
                tags=cfg.get("tags", []),
            )
        )
        log(f"[catalog] single: {name}")
    except Exception as ex:
        log(f"[catalog] single error: {ex}")
    return out

def build_catalog():
    raw = []
    for _, cfg in SITE_MAP.items():
        if cfg.get("mode") == "single":
            raw.extend(scrape_single(cfg))
        else:
            raw.extend(scrape_outlinks(cfg))

    # de-dup by lower(name)|domain
    def kfn(x):
        nm = (x.get("name") or "").strip().lower()
        domain = domain_of(x.get("url") or "")
        return f"{nm}|{domain}" if nm and domain else None

    seen = set()
    deduped = []
    for x in raw:
        k = kfn(x)
        if not k or k in seen:
            continue
        seen.add(k)
        deduped.append(x)

    bucketed = {"programs": [], "experts": [], "institutions": []}
    for rec in deduped:
        t = (rec.get("__type") or "").lower()
        if t == "program":
            bucketed["programs"].append(
                {
                    "name": rec.get("name"),
                    "category": "—",
                    "description": "External resource from roadmap",
                    "location": "—",
                    "url": rec.get("url"),
                    "image": rec.get("image"),
                    "tags": rec.get("tags", []),
                }
            )
        elif t == "expert":
            bucketed["experts"].append(
                {
                    "name": rec.get("name"),
                    "specialty": "—",
                    "location": rec.get("location") or "—",
                    "rating": None,
                    "url": rec.get("url"),
                    "image": rec.get("image"),
                    "tags": rec.get("tags", []),
                }
            )
        else:
            bucketed["institutions"].append(
                {
                    "name": rec.get("name"),
                    "focus": "Longevity / Clinic / Biotech",
                    "location": rec.get("location") or "—",
                    "url": rec.get("url"),
                    "image": rec.get("image"),
                    "tags": rec.get("tags", []),
                }
            )

    (DATA_DIR / "catalog.json").write_text(json.dumps(bucketed, indent=2), encoding="utf-8")
    log(
        f"[catalog] Wrote {len(bucketed['programs'])} programs, "
        f"{len(bucketed['experts'])} experts, {len(bucketed['institutions'])} institutions"
    )


# -------------------------- Main --------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--query",
        type=str,
        default="longevity OR aging OR chronic disease treatment OR randomized trial",
        help="Evidence/news query (used for Google News, PubMed, plus base feeds).",
    )
    ap.add_argument(
        "--build-catalog",
        action="store_true",
        help="Also scrape directory of programs/experts/institutions and write catalog.json",
    )
    ap.add_argument(
        "--weekly-only",
        action="store_true",
        help="If set, only build the catalog on Sundays (UTC).",
    )
    args = ap.parse_args()

    # Build evidence + archives + logs
    build(args.query)

    # Weekly directory scrape if asked
    if args.build_catalog:
        if args.weekly_only:
            if datetime.utcnow().weekday() == 6:  # Sunday (Mon=0..Sun=6)
                build_catalog()
            else:
                log("[catalog] Skipped (weekly-only; not Sunday UTC)")
        else:
            build_catalog()
