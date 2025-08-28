# Universal Sci & Tech Breakthrough Beat — Live Scraper

Builds a static site in `output/` with searchable science & health news.

## Local run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py --query "longevity OR aging OR chronic disease treatment OR randomized trial"
cd output && python3 -m http.server 8000
