from feedparser import datetime as fp_datetime
import html

# Outside loop
seen_links = set()  # Prevent duplicate articles

for category, url in FEEDS.items():
    cleaned_url = url.strip()
    print(f"Fetching {category}: {cleaned_url}")
    feed = feedparser.parse(cleaned_url)

    if not feed.entries:
        print(f"⚠️ No entries for {category}")
        continue

    for entry in feed.entries[:2]:
        # Skip if we've seen this article
        link = entry.link
        if link in seen_links:
            continue
        seen_links.add(link)

        title = html.escape(entry.title)
        summary = html.escape(entry.get("summary", "No summary available."))
        preview = truncate(summary, 200)

        # Parse date properly
        raw_date = entry.get('published_parsed')
        if raw_date:
            pub_date = datetime(*raw_date[:6])
        else:
            pub_date = datetime.now()
        pub_day = pub_date.strftime("%Y-%m-%d")

        # Generate safe slug
        slug_base = "".join(c for c in title[:50] if c.isalnum() or c in " -_")
        slug_base = slug_base.replace(' ', '-').replace('--', '-').lower()
        slug = f"{pub_day}-{category.lower()}-{slug_base}"
        filename = f"output/posts/{slug}.html"
