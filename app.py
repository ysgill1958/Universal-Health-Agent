import os
from datetime import datetime

# Output folders
os.makedirs("posts", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Example evidence posts (in real loop, you'd generate/fetch these)
posts = [
    {"title": "Health Tip: Stay Hydrated", "content": "Drink at least 8 glasses of water a day."},
    {"title": "AI in Healthcare", "content": "AI agents are helping doctors detect diseases earlier."},
]

# Generate unique filenames for posts
generated_files = []
for i, post in enumerate(posts, 1):
    slug = f"post-{datetime.now().strftime('%Y-%m-%d')}-{i}.html"
    filepath = os.path.join("posts", slug)
    generated_files.append((slug, post["title"]))

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{post["title"]}</title>
    <link rel="stylesheet" href="../static/style.css">
</head>
<body>
    <div class="container">
        <h1>{post["title"]}</h1>
        <p><em>{datetime.now().strftime('%B %d, %Y')}</em></p>
        <div class="content">{post["content"]}</div>
        <p><a href="../index.html">← Back to homepage</a></p>
    </div>
</body>
</html>""")

# Generate homepage
with open("index.html", "w", encoding="utf-8") as f:
    f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Universal Health Agent Blog</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <div class="container">
        <h1>Universal Health Agent Blog</h1>
        <p>Auto-generated updates from the agent loop.</p>
        <ul>
            {''.join([f'<li><a href="posts/{slug}">{title}</a></li>' for slug, title in generated_files])}
        </ul>
    </div>
</body>
</html>""")

# Basic CSS (only write if file doesn't exist yet)
if not os.path.exists("static/style.css"):
    with open("static/style.css", "w") as f:
        f.write("""
body {
    font-family: Arial, sans-serif;
    background: #f9f9f9;
    margin: 0;
    padding: 0;
}
.container {
    max-width: 700px;
    margin: auto;
    background: #fff;
    padding: 20px;
    border-radius: 8px;
}
h1 { color: #2c3e50; }
a { color: #0077cc; text-decoration: none; }
a:hover { text-decoration: underline; }
ul { list-style-type: none; padding: 0; }
li { margin: 10px 0; }
""")
