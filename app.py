import os
import feedparser
from datetime import datetime
import re
import html  # For escaping

# Feeds to track
FEEDS = {
    "Health": "https://www.sciencedaily.com/rss/health_medicine.xml",
    "Science": "https://www.sciencedaily.com/rss/top/science.xml",
    "AI": "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
    "Medicine": "https://www.sciencedaily.com/rss/health_medicine.xml"
}

# Setup folders
os.makedirs("output/posts", exist_ok=True)
open("output/.nojekyll", "w").close()

today = datetime.now().strftime("%Y-%m-%d")
posts_by_date = {}

def truncate(text, length=200):
    if not text:
        return "No summary available."
    if len(text) > length:
        return text[:length].rsplit(' ', 1)[0] + '...'
    return text

def clean_filename(text, max_len=50):
    text = html.unescape(text)  # Optional: decode HTML entities
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '-', text)  # Replace invalid chars
    text = re.sub(r'-+', '-', text)  # Deduplicate
    return text.strip('-')[:max_len].lower()

seen_links = set()  # Avoid duplicates

for category, url in FEEDS.items():
    cleaned_url = url.strip()
    print(f"📥 Fetching {category} feed...")
    feed = feedparser.parse(cleaned_url)

    if not feed.entries:
        print(f"❌ No entries in {category} feed (check URL or network)")
        continue

    for entry in feed.entries[:2]:
        link = entry.link
        if link in seen_links:
            continue
        seen_links.add(link)

        title = html.escape(entry.title)
        summary = html.escape(entry.get("summary", entry.get("description", "")))
        preview = truncate(summary, 200)

        # Parse date safely
        raw_date = entry.get('published_parsed')
        if raw_date:
            pub_date = datetime(*raw_date[:6])
        else:
            print(f"⚠️ No parseable date for: {entry.title[:50]}... using today")
            pub_date = datetime.now()
        pub_day = pub_date.strftime("%Y-%m-%d")

        # Generate safe slug
        slug_base = clean_filename(title)
        slug = f"{pub_day}-{category.lower()}-{slug_base}"
        filename = f"output/posts/{slug}.html"

        # Write post
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
  <p><a href="{link}" target="_blank">Read full article</a></p>
  <br><a href="../index.html">← Back to Home</a>
</body>
</html>"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(post_html)
            print(f"✅ Created: {slug}")
        except OSError as e:
            print(f"❌ Failed to write file: {filename}")
            print(f"   Error: {e}")
            continue

        posts_by_date.setdefault(pub_day, []).append((title, slug, category, preview))

# Build index.html
index_html = """<!DOCTYPE html>
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

index_html += f"<p><i>Auto-updated on {today}</i></p>\n</body>\n</html>"

with open("output/index.html", "w", encoding="utf-8") as f:
    f.write(index_html)

print(f"\n🎉 Success! Generated {len(seen_links)} unique posts across {len(posts_by_date)} days.")
