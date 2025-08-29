# Placeholder for crawler.py
import json
import os
import random
import time
from collections import deque
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup, Tag

# ---------------------------
# I. CONFIGURATION PARAMETERS
# ---------------------------

PORTAL_ENTRY_URL = "https://pureportal.coventry.ac.uk/en/organisations/fbl-school-of-economics-finance-and-accounting/publications"
PORTAL_ROOT = "https://pureportal.coventry.ac.uk"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

OUTPUT_FILE = "coventry_publications.json"
MAX_RETRY_ATTEMPTS = 3
WAIT_TIMEOUT = 30
REST_INTERVAL = 5

# ---------------------------
# II. HELPER FUNCTIONS
# ---------------------------

def extract_authors(detail_soup, base_url):
    """From a publication’s detail page, extract the list of authors and their profile URLs (if present)."""
    author_records = []
    author_paragraph = detail_soup.select_one("p.relations.persons")

    if not author_paragraph:
        return []

    for element in author_paragraph.contents:
        if isinstance(element, Tag) and element.name == "a":
            name = element.get_text(strip=True)
            url = urljoin(base_url, str(element.get("href", "")))
            if name:
                author_records.append({"name": name, "url": url})
        elif isinstance(element, str):
            # Capture non-hyperlinked names as plain text authors.
            for possible_name in element.split(","):
                clean_name = possible_name.strip(" ,")
                if clean_name:
                    author_records.append({"name": clean_name, "url": None})

    return author_records


def extract_abstract(detail_soup):
    """Extract the abstract from the publication page if available."""
    abstract_box = detail_soup.find("div", class_="rendering_researchoutput_abstractportal")
    if abstract_box:
        text_block = abstract_box.find("div", class_="textblock")
        if text_block:
            return text_block.get_text(strip=True)
    return ""


def configure_driver():
    """Prepare a silent, headless Chrome driver for crawling."""
    options = Options()
   # options.add_argument("--headless=new")
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(log_output=os.devnull)
    driver = webdriver.Chrome(service=service, options=options)
    return driver, WebDriverWait(driver, WAIT_TIMEOUT)


# ---------------------------
# III. THE CRAWLER NARRATIVE
# ------------------a---------

def crawl_portal():
    print("\n=== Coventry University PurePortal Crawler Initiated ===\n")

    driver, waiter = configure_driver()

    # Step 1: Collect publication URLs across paginated list pages
    print("Phase One: Mapping the terrain of publication listings...")
    queue = deque([PORTAL_ENTRY_URL])
    discovered_pages = {PORTAL_ENTRY_URL}
    collected_publications = []

    try:
        while queue:
            current_page = queue.popleft()
            print(f"\nVisiting listing page: {current_page}")

            success = False
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    driver.get(current_page)

                    if len(discovered_pages) == 1:
                        # Handle cookies only once
                        try:
                            WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-accept-btn-handler"))
                            ).click()
                            print("Cookie banner dismissed.")
                        except Exception:
                            pass

                    waiter.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.list-result-item")))
                    success = True
                    break
                except (TimeoutException, WebDriverException) as e:
                    print(f"Attempt {attempt + 1} failed for {current_page}: {e}")
                    time.sleep(random.uniform(REST_INTERVAL, REST_INTERVAL + 2))

            if not success:
                print(f"Abandoning page {current_page} after repeated failures.")
                continue

            soup = BeautifulSoup(driver.page_source, "html.parser")
            publications = soup.find_all("li", class_="list-result-item")

            print(f"Discovered {len(publications)} candidate publications on this page.")

            for pub in publications:
                title_tag = pub.find("h3", class_="title")
                if title_tag and title_tag.a:
                    title = title_tag.get_text(strip=True)
                    url = urljoin(PORTAL_ROOT, str(title_tag.a["href"]))
                    date_tag = pub.find("span", class_="date")
                    date = date_tag.get_text(strip=True) if date_tag else "N/A"
                    collected_publications.append({"title": title, "url": url, "date": date})
                    print(f"  • {title} ({date})")

            next_link = soup.find("a", class_="nextLink")
            if next_link and "href" in next_link.attrs:
                next_url = urljoin(PORTAL_ROOT, str(next_link["href"]))
                if next_url not in discovered_pages:
                    discovered_pages.add(next_url)
                    queue.append(next_url)

            time.sleep(random.uniform(REST_INTERVAL, REST_INTERVAL + 2))

        print(f"\nPhase One Complete: {len(collected_publications)} publications queued for detail scraping.\n")

        # Step 2: Visit each publication page for authors and abstracts
        print("Phase Two: Entering individual publications to harvest authorship and abstracts...\n")
        enriched_publications = []

        for idx, record in enumerate(collected_publications, 1):
            print(f"[{idx}/{len(collected_publications)}] Inspecting: {record['title']}")
            success = False

            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    driver.get(record["url"])
                    waiter.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.relations.persons")))
                    detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                    record["authors"] = extract_authors(detail_soup, PORTAL_ROOT)
                    record["abstract"] = extract_abstract(detail_soup)
                    success = True
                    print("   ↳ Success: authors and abstract retrieved.")
                    break
                except (TimeoutException, WebDriverException) as e:
                    print(f"   Attempt {attempt + 1} failed for {record['url']}: {e}")
                    time.sleep(random.uniform(REST_INTERVAL, REST_INTERVAL + 2))

            if not success:
                record["authors"] = []
                record["abstract"] = ""
                print("   ↳ Failed to capture details after all retries.")

            enriched_publications.append(record)
            time.sleep(random.uniform(REST_INTERVAL, REST_INTERVAL + 2))

    finally:
        driver.quit()
        print("\nBrowser session closed.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        json.dump(enriched_publications, outfile, indent=4, ensure_ascii=False)

    print(f"\n=== Crawling Complete ===\nCollected {len(enriched_publications)} publications.")
    print(f"Data archived at: {OUTPUT_FILE}")


if __name__ == "__main__":
    crawl_portal()
