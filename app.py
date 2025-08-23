import os
import feedparser
from datetime import datetime
from feedparser import datetime as fp_datetime

# Feeds to track — cleaned URLs
FEEDS = {
    "Health": "https://www.sciencedaily.com/rss/health_medicine.xml",
    "Science": "https://www.sciencedaily.com/rss/top/science.xml",
    "AI": "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
    "Medicine": "https://www.sciencedaily.com/rss/health_medicine.xml"
}

os.makedirs("output/posts", exist_ok=True)
open("output/.nojekyll", "w").close()

today = datetime.now().strftime("%Y-%m-%d")
posts_by_date = {}

def truncate(text, length=200):
    if not text:
        return "No summary available."
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."

# Loop through feeds
for category, url in FEEDS.items():
    cleaned_url = url.strip()
    print(f"Fetching {category}: {cleaned_url}")
    feed = feedparser.parse(cleaned_url)

    if not feed.entries:
        print(f"⚠️ No entries for {category}")
        continue

    for entry in feed.entries[:2]:
        title = entry.title
        link = entry.link
        summary = entry.get("summary", "No summary available.")
        preview = truncate(summary, 200)

        # Parse publication date safely
        raw_date = entry.get("published_parsed")
        if raw_date:
            pub_date = datetime(*raw_date[:6])
        else:
            pub_date = datetime.now()
        pub_day = pub_date.strftime("%Y-%m-%d")

        # Create unique slug (prevent duplicates)
        slug_base = title[:40].replace(' ', '-').replace('/', '_')
        slug = f"{pub_day}-{category.lower()}-{slug_base}"
        filename = f"output/posts/{slug}.html"

        # Write post HTML
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
  <p>Read more: <a href="{link}" target="_blank">{link}</a></p>
  <br><a href="../index.html">← Back to Home</a>
</body>
</html>
"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(post_html)

        posts_by_date.setdefault(pub_day, []).append((title, slug, category, preview))

# Generate index.html
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

print(f"✅ Generated {sum(len(v) for v in posts_by_date.values())} posts across {len(posts_by_date)} dates.")
