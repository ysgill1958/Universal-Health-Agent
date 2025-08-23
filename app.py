import feedparser
d = feedparser.parse("https://www.sciencedaily.com/rss/health_medicine.xml")
print(d.feed.title)
for e in d.entries[:1]:
    print("Title:", e.title)
    print("Link:", e.link)
    print("Published:", e.published)
    print("Published Parsed:", e.published_parsed)
