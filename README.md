# Universal Sci & Tech Breakthrough Beat — Global S&T Info Hub

A lightweight static site that aggregates S&T / health evidence & news, adds thumbnails, tags, and builds searchable archives.

## Quick start
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Build latest + archives (shows NEW badge for last 24h)
python app.py --query "longevity OR aging OR chronic disease treatment OR randomized trial"

# (Optional) Build the catalog of programs/experts/institutions too (weekly)
python app.py --query "longevity OR aging OR chronic disease treatment OR randomized trial" --build-catalog --weekly-only
```

Open `output/index.html` in your browser.
