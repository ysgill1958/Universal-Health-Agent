import os, json, datetime

def run_agent_loop():
    # Dummy evidence fetcher for demo
    return {
        "title": "New Breakthrough in Longevity",
        "summary": "Study shows traditional therapy improves lifespan.",
        "link": "https://example.com/study"
    }

def save_outputs(evidence):
    # Save JSON log
    with open("results.json", "a") as f:
        f.write(json.dumps(evidence) + "\n")

    # Save Markdown post
    os.makedirs("posts", exist_ok=True)
    date_str = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = f"posts/{date_str}.md"
    with open(filename, "w") as f:
        f.write(f"# {evidence['title']}\n\n")
        f.write(f"**Summary:** {evidence['summary']}\n\n")
        f.write(f"[Read more]({evidence['link']})\n")

def regenerate_index():
    # Build homepage with list of posts
    posts_dir = "posts"
    post_files = sorted(os.listdir(posts_dir), reverse=True) if os.path.exists(posts_dir) else []

    with open("index.md", "w") as f:
        f.write("# Health Evidence Agent\n\n")
        f.write("This site auto-publishes the latest findings about chronic disease therapies and longevity.\n\n")
        f.write("## Latest Posts\n\n")

        if not post_files:
            f.write("_No posts yet. Come back soon!_\n")
        else:
            for post in post_files:
                title_line = ""
                with open(os.path.join(posts_dir, post)) as pf:
                    for line in pf:
                        if line.startswith("# "):
                            title_line = line.strip("# ").strip()
                            break
                date_label = post.replace(".md", "")
                f.write(f"- [{title_line}](./posts/{post}) — {date_label}\n")

if __name__ == "__main__":
    evidence = run_agent_loop()
    save_outputs(evidence)
    regenerate_index()
