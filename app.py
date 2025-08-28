# app.py — Universal Sci & Tech Breakthrough Beat
# Builds: output/data/items.json, monthly archives (thumb+summary+NEW),
# archive index with global search, logs, and (weekly) directory catalog.

import re, json, hashlib, argparse, email.utils as eut
from time import mktime, sleep
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests, feedparser
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("output")
DATA_DIR = OUTPUT_DIR / "data"
STATIC_DIR = OUTPUT_DIR / "static"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
for p in (OUTPUT_DIR, DATA_DIR, STATIC_DIR, ARCHIVE_DIR):
    p.mkdir(parents=True, exist_ok=True)

(OUTPUT_DIR / ".nojekyll").write_text("")
LOG_FILE = DATA_DIR / "logs.txt"

def now_utc_str(): return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
def log(msg): 
    line=f"[{now_utc_str()}] {msg}"
    print(line); open(LOG_FILE,"a",encoding="utf-8").write(line+"\n")

def clean_text(s): return re.sub(r"\s+"," ", re.sub(r"<.*?>"," ", s or "")).strip()
def truncate(s,n=360): s=clean_text(s); return s if len(s)<=n else s[:n].rsplit(" ",1)[0]+"…"
def normalize_key(title,link): 
    host=urlparse(link or "").netloc.lower()
    t=re.sub(r"[^a-z0-9 ]+","", (title or "").lower().strip())
    return hashlib.sha1(f"{host}|{t}".encode()).hexdigest()

HEADERS={"User-Agent":"Mozilla/5.0 (USTBB/3.0; +GitHubPages Agent)"}

def get_og_image(url,timeout=8):
    try:
        r=requests.get(url,headers=HEADERS,timeout=timeout); r.raise_for_status()
        soup=BeautifulSoup(r.content,"lxml")
        for css,attr in [('meta[property="og:image"]',"content"),
                         ('meta[name="twitter:image"]',"content")]:
            m=soup.select_one(css)
            if m and m.get(attr): return urljoin(url,m.get(attr).strip())
    except Exception: pass
    return None

def google_news_feed(query): 
    return f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
def pubmed_feed(query): 
    return f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?db=pubmed&term={requests.utils.quote(query)}&sort=date"

BASE_FEEDS=[
 ("NIH","https://www.nih.gov/news-events/news-releases/rss.xml"),
 ("WHO","https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml"),
 ("Nature","https://www.nature.com/nature.rss"),
 ("BMJ","https://www.bmj.com/latest.xml"),
 ("Lancet","https://www.thelancet.com/rssfeed/lancet_current.xml"),
]

def parse_date(e):
    for k in ("published_parsed","updated_parsed"):
        if e.get(k): return datetime.utcfromtimestamp(mktime(e[k])).strftime("%Y-%m-%d %H:%M:%S")
    for k in ("published","updated","dc_date"):
        if e.get(k):
            try:
                tt=eut.parsedate_to_datetime(e[k])
                if tt.tzinfo: tt=tt.astimezone(timezone.utc).replace(tzinfo=None)
                return tt.strftime("%Y-%m-%d %H:%M:%S")
            except: pass
    return ""

def fetch_feed(source,url,limit,delay):
    items=[]
    try:
        resp=requests.get(url,headers=HEADERS,timeout=20); resp.raise_for_status()
        fp=feedparser.parse(resp.content)
        for e in fp.entries[:limit]:
            items.append({
              "source":source,
              "title":(e.get("title") or "").strip(),
              "link":(e.get("link") or "").strip(),
              "summary":truncate(e.get("summary") or ""),
              "date":parse_date(e),
              "image":None
            })
        log(f"{source}: {len(items)}")
    except Exception as ex: log(f"Fetch error {source}: {ex}")
    sleep(delay); return items

def aggregate(query,max_total=500,thumb_budget=200):
    feeds=[("Google News",google_news_feed(query)),("PubMed",pubmed_feed(query))]+BASE_FEEDS
    all_items=[]; 
    for s,u in feeds: all_items+=fetch_feed(s,u,50,0.4)
    seen=set(); deduped=[]
    for it in all_items:
        k=normalize_key(it["title"],it["link"])
        if k in seen: continue
        seen.add(k); deduped.append(it)
        if len(deduped)>=max_total: break
    log(f"Deduped: {len(deduped)}")
    for it in deduped:
        if thumb_budget<=0: break
        img=get_og_image(it["link"])
        if img: it["image"]=img; thumb_budget-=1
    deduped.sort(key=lambda x:x.get("date") or "", reverse=True)
    return deduped

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--query",required=True); args=ap.parse_args()
    items=aggregate(args.query)
    (DATA_DIR/"items.json").write_text(json.dumps(items,indent=2),encoding="utf-8")
    log(f"Wrote {len(items)} items → {DATA_DIR/'items.json'}")
