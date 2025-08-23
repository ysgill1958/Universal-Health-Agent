import feedparser
import re
import os
import html

# Test with one feed
url = "https://www.sciencedaily.com/rss/health_medicine.xml"
print("📡 Fetching feed...")
feed = feedparser.parse(url)

if not feed.entries:
    print("❌ ERROR: No entries loaded. Check:")
    print("   - Internet connection")
    print("   - URL validity")
    print("   - Firewall or network restrictions")
    exit()

entry = feed.entries[0]
print("✅ Feed loaded!")
print("Title:", entry.title)
print("Link:", entry.link)
print("PubDate (raw):", entry.published)
print("Published Parsed:", entry.published_parsed)

# Try to generate filename
title = entry.title
category = "health"
raw_date = entry.published_parsed

if raw_date:
    pub_day = f"{raw_date.tm_year}-{raw_date.tm_mon:02d}-{raw_date.tm_mday:02d}"
else:
    from datetime import datetime
    pub_day = datetime.now().strftime("%Y-%m-%d")

# Clean title for filename
def clean_filename(text, max_len=50):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', text)  # Replace bad chars
    text = re.sub(r'_+', '_', text)
    return text.strip('_')[:max_len]

slug_base = clean_filename(title)
slug = f"{pub_day}-health-{slug_base}.html"
filename = f"output/posts/{slug}"

print("Generated filename:", filename)

# Try to write
try:
    os.makedirs("output/posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"<h1>{html.escape(entry.title)}</h1>\n")
        f.write(f"<p>{entry.summary}</p>\n")
    print("✅ File created successfully!")
except Exception as e:
    print(f"❌ FAILED to write file: {e}")
