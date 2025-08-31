import os, time, schedule, subprocess

DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

def run_pipeline():
    print('Running weekly crawl + index...')
    subprocess.run(['python', 'crawler.py', '--max-pages', '50', '--workers', '6', '--outdir', DATA_DIR], check=True)
    subprocess.run(['python', 'indexer.py', '--in', f'{DATA_DIR}/publications.jsonl', '--index', f'{DATA_DIR}/index.json', '--postings', f'{DATA_DIR}/postings.json'], check=True)
    print('Done.')

# Every Monday at 03:30
schedule.every().monday.at("03:30").do(run_pipeline)

if __name__ == '__main__':
    print('Scheduler started. Press Ctrl+C to stop.')
    while True:
        schedule.run_pending()
        time.sleep(5)
