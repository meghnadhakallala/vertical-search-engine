# scheduler.py
import schedule
import time
import logging
from crawler import crawl_portal
from invertedindexer import InvertedIndexer

# -------------------------------
# Logging configuration
# -------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] | %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

# -------------------------------
# Pipeline
# -------------------------------
def run_pipeline():
    """Run the crawler and indexer pipeline"""
    try:
        logging.info("Pipeline started.")

        # Run the crawler
        logging.info("Launching crawler — collecting fresh documents...")
        crawl_portal()
        logging.info("Crawler completed. New data harvested.")

        # Run the indexer
        logging.info("Activating indexer — rebuilding the inverted index...")
        indexer = InvertedIndexer()
        indexer.build_index('coventry_publications.json')
        indexer.save_index('inverted_index.pkl')
        logging.info("Indexer completed. Search index is up-to-date.")

        logging.info("Pipeline finished successfully.")

    except Exception:
        logging.exception("Pipeline failure detected!")

# -------------------------------
# Scheduler setup
# -------------------------------
def main():
    # Schedule weekly (Friday at 06:00)
    schedule.every().friday.at("06:00").do(run_pipeline)
    logging.info("Scheduler initialized — runs every Friday at 06:00 AM.")

    # Immediate run on startup
    logging.info("Immediate startup run triggered...")
    run_pipeline()

    # Keep script alive for schedule
    while True:
        schedule.run_pending()
        time.sleep(60)  # check every minute


if __name__ == "__main__":
    main()
 