import os
import sys

# Minimal script to test linkedin scraping outside the API
# Usage: set LINKEDIN_EMAIL and LINKEDIN_PASSWORD env vars, then run:
#   python backend/scripts/test_linkedin_scrape.py <profile_url>

sys.path.append(os.path.abspath("backend"))

from app.worker.tasks.data_ingestion import scrape_linkedin_profile  # type: ignore

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/test_linkedin_scrape.py <linkedin_profile_url>")
        sys.exit(1)
    url = sys.argv[1]
    email = os.getenv("LINKEDIN_EMAIL")
    pwd = os.getenv("LINKEDIN_PASSWORD")
    if not email or not pwd:
        print("ERROR: Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables.")
        sys.exit(2)
    print(f"Engine: {os.getenv('SCRAPER_ENGINE', 'selenium')}\nEmail found: {bool(email)}")
    data = scrape_linkedin_profile(url)
    print("\n=== Scrape Result ===")
    print(data)
