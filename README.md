# CovScholar — Vertical Search for Coventry (FBL: Economics, Finance & Accounting)

A polite crawler + lightweight search engine that indexes publications where **at least one co‑author**
is a member of Coventry University's **School of Economics, Finance and Accounting** on Pure Portal.

## What you get
- `crawler.py` — Polite crawler that respects `robots.txt`, rate‑limits, and paginates through the org's **Publications**.
- `preprocess.py` — Tokenization, stopword removal, simple stemming, and query normalization.
- `indexer.py` — Builds a TF‑IDF inverted index and metadata store; deduplicates by DOI if available, else title+year.
- `search_cli.py` — Terminal search with relevance ranking and clickable links in most terminals.
- `search_app.py` — Streamlit UI that feels like a tiny Google Scholar.
- `scheduler.py` — Weekly re‑crawl + re‑index using `schedule` (or use cron/systemd on servers).
- `data/` — JSONL records of publications, index files.

## Quick start

# 1) Build (crawl + index)
python crawler.py --base https://pureportal.coventry.ac.uk/en/organisations/fbl-school-of-economics-finance-and-accounting/publications/ --out data/publications.jsonl
python indexer.py --in data/publications.jsonl --index data/index.json --postings data/postings.json

# 2a) Search in terminal
python search_cli.py "financial stability climate risk" --topk 20

# 2b) Run the Streamlit app (GUI)
streamlit run search_app.py
```

## Scheduling (once per week)
- Option A (Python): `python scheduler.py` (keeps a process running; use pm2/supervisor/screen/tmux)
- Option B (Cron): Run `python crawler.py` then `python indexer.py` every Monday at 03:00.
  Example crontab:
  ```
  0 3 * * 1 /path/to/python /path/to/covscholar/crawler.py --base https://pureportal.coventry.ac.uk/en/organisations/fbl-school-of-economics-finance-and-accounting/publications/ --out /path/to/covscholar/data/pubs.jsonl && /path/to/python /path/to/covscholar/indexer.py --in /path/to/covscholar/data/pubs.jsonl --index /path/to/covscholar/data/index.json --postings /path/to/covscholar/data/postings.json
  ```

## Notes
- The crawler starts from the department's Publications page, so by construction at least one co‑author is from the target department.
- Politeness: `robots.txt` respected; default delay 2–4s with jitter; custom `User-Agent` string; backoff on errors.
- If Pure's HTML changes, adjust the CSS selectors in `crawler.py` (they’re grouped in one spot).
- The search engine performs basic preprocessing (lowercasing, tokenization, stopwords, light stemming) and TF‑IDF ranking.
- All data are stored as JSON/JSONL for transparency and easy debugging.
