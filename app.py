import os
from datetime import datetime

# Make sure output directories exist
os.makedirs("output/posts", exist_ok=True)

# Create a homepage (index.html)
with open("output/index.html", "w") as f:
    f.write("""
    <html>
    <head><title>Universal Health Agent</title></head>
    <body>
      <h1>Welcome to Universal Health Agent</h1>
      <ul>
        <li><a href="posts/2025-08-20-my-first-post.html">My First Post</a></li>
        <li><a href="posts/2025-08-20-another-post.html">Another Post</a></li>
      </ul>
    </body>
    </html>
    """)

# Example post 1
with open("output/posts/2025-08-20-my-first-post.html", "w") as f:
    f.write("""
    <html>
    <head><title>My First Post</title></head>
    <body>
      <h1>My First Post</h1>
      <p>Hello, this is my first generated post!</p>
      <a href="../index.html">Back to Home</a>
    </body>
    </html>
    """)

# Example post 2
with open("output/posts/2025-08-20-another-post.html", "w") as f:
    f.write("""
    <html>
    <head><title>Another Post</title></head>
    <body>
      <h1>Another Post</h1>
      <p>This is another example blog entry.</p>
      <a href="../index.html">Back to Home</a>
    </body>
    </html>
    """)

print("✅ Site generated in output/")
