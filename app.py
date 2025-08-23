import os
import feedparser
from datetime import datetime
import re
import html

# --- CONFIG ---
FEEDS = {
    "Health": "https://www.sciencedaily.com/rss/health_medicine.xml",
    "Science": "https://www.sciencedaily.com/rss/top/science.xml",
    "AI": "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
    "Medicine": "https://www.sciencedaily.com/rss/health_medicine.xml"
}

OUTPUT_DIR = "output"
POSTS_DIR = os.path.join(OUTPUT_DIR, "posts")

# Create dirs
os.makedirs(POSTS_DIR, exist_ok=True)
open(os.path.join(OUTPUT_DIR, ".nojekyll"), "w").close()

# Clean text for filenames
def clean_filename(text, max_len=60):
    text = html.unescape(text)
    # Replace invalid chars with underscore
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', text)
    text = re.sub(r'_+', '_', text)  # Deduplicate
    return text.strip('_')[:max_len].lower()

def truncate(text, length=200):
    if not text:
        return "No summary available."
    text = re.sub(r'<[^>]+>', '', text)  # Strip HTML if any
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + '...'

# Track seen articles by GUID or link
seen_links = set()
posts_by_date = {}

for category, url in FEEDS.items():
    print(f"📡 Fetching {category}...")
    feed = feedparser.parse(url.strip())

    if not feed.entries:
        print(f"❌ No entries from {url}")
        continue

    for entry in feed.entries[:2]:
        # Use GUID or link as ID
        uid = entry.get('guid') or entry.link
        if uid in seen_links:
            continue
        seen_links.add(uid)

        title = html.escape(entry.title)
        summary = html.escape(entry.get("summary", entry.get("description", "")))
        preview = truncate(summary, 200)

        # Parse date
        raw_date = entry.get('published_parsed')
        if raw_date:
            pub_date = datetime(*raw_date[:6])
        else:
            print(f" ⚠️ No date for: {title[:50]}...")
            pub_date = datetime.now()
        pub_day = pub_date.strftime("%Y-%m-%d")

        # Generate safe slug
        safe_title = clean_filename(entry.title.replace(' ', '-'))
        slug = f"{pub_day}-{category.lower()}-{safe_title}"
        filename = os.path.join(POSTS_DIR, f"{slug}.html")

        # Write post
        try:
            post_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
</head>
<body>
  <h1>{title}</h1>
  <p><i>{category} • Published {pub_day}</i></p>
  <p>{summary}</p>
  <p><a href="{entry.link}" target="_blank">Read full article</a></p>
  <br><a href="../index.html">← Back to Home</a>
</body>
</html>"""
            with open(filename, "w", encoding="utf-8") as f:
                f.write(post_html)
            print(f"✅ Saved: {slug}")

        except OSError as e:
            print(f"❌ OS Error writing {filename}: {e}")
            continue
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            continue

        posts_by_date.setdefault(pub_day, []).append((title, slug, category, preview))

# Build index.html
index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Universal Health Agent Blog</title>
</head>
<body>
  <h1>Universal Health Agent Blog</h1>
  <h2>Latest Breakthroughs</h2>
"""

for pub_day in sorted(posts_by_date.keys(), reverse=True):
    index_html += f"<h3>{pub_day}</h3>\n<ul>\n"
    for title, slug, category, preview in posts_by_date[pub_day]:
        index_html += f"""  <li>[{category}] <a href="posts/{slug}.html">{title}</a><br>
      <small>{preview}</small></li>\n"""
    index_html += "</ul>\n"

index_html += f"<p><i>Auto-updated on {datetime.now().strftime('%Y-%m-%d')}</i></p>\n</body>\n</html>"

with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(index_html)

print(f"\n🎉 SUCCESS! Generated {len(seen_links)} unique posts across {len(posts_by_date)} days.")
