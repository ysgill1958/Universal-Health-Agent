import os
from datetime import datetime

# Ensure output directories exist
os.makedirs("output/posts", exist_ok=True)

# Create .nojekyll file so GitHub Pages works correctly
open("output/.nojekyll", "w").close()

# Today's date for post slug
today = datetime.now().strftime("%Y-%m-%d")

# Example daily post (replace with real Universal Health Agent content)
new_post = {
    "title": f"Daily Health Update - {today}",
    "slug": f"{today}-daily-update",
    "content": f"<p>This is the automatically generated blog post for {today}. "
               "Future versions will include Universal Health Agent reports, news, and health tips.</p>"
}

# Save today's post
post_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{new_post['title']}</title>
</head>
<body>
  <h1>{new_post['title']}</h1>
  {new_post['content']}
  <br><a href="../index.html">← Back to Home</a>
</body>
</html>
"""
with open(f"output/posts/{new_post['slug']}.html", "w", encoding="utf-8") as f:
    f.write(post_html)

# Build index.html (latest first + preview)
post_files = sorted(os.listdir("output/posts"), reverse=True)
index_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Universal Health Agent Blog</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 20px; }
    h1 { color: darkgreen; }
    .post-preview { border-bottom: 1px solid #ddd; margin-bottom: 20px; padding-bottom: 10px; }
    .post-preview h2 { margin: 0; }
    .post-preview p { color: #555; }
  </style>
</head>
<body>
  <h1>Universal Health Agent Blog</h1>
"""

for file in post_files:
    filepath = os.path.join("output/posts", file)
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    # Extract title and snippet (first 150 characters of body text)
    title_start = html.find("<h1>") + 4
    title_end = html.find("</h1>")
    title = html[title_start:title_end]

    body_start = html.find("<p>") + 3
    body_end = html.find("</p>")
    snippet = html[body_start:body_end][:150] + "..."

    index_content += f"""
  <div class="post-preview">
    <h2><a href="posts/{file}">{title}</a></h2>
    <p>{snippet}</p>
  </div>
"""

index_content += """</body>
</html>
"""

with open("output/index.html", "w", encoding="utf-8") as f:
    f.write(index_content)

print(f"✅ Blog updated with new post: {new_post['title']}")
