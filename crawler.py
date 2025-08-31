import argparse, json, os, time, re, unicodedata, sys
from math import ceil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Parallelism
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- Config ----------
MAIN_PORTAL_URL = "https://pureportal.coventry.ac.uk"
PUBLICATIONS_BASE_URL = f"{MAIN_PORTAL_URL}/en/organisations/fbl-school-of-economics-finance-and-accounting/publications/"


def configure_browser_options(run_headless: bool, use_legacy_mode: bool = False) -> Options:
    browser_opts = Options()
    if run_headless:
        browser_opts.add_argument("--headless" + ("" if use_legacy_mode else "=new"))
    browser_opts.add_argument("--window-size=1366,900")
    browser_opts.add_argument("--disable-gpu")
    browser_opts.add_argument("--no-sandbox")
    browser_opts.add_argument("--disable-dev-shm-usage")
    browser_opts.add_argument("--lang=en-US")
    browser_opts.add_argument("--disable-notifications")
    browser_opts.add_argument("--no-first-run")
    browser_opts.add_argument("--no-default-browser-check")
    browser_opts.add_argument("--disable-extensions")
    browser_opts.add_argument("--disable-popup-blocking")
    browser_opts.add_argument("--disable-renderer-backgrounding")
    browser_opts.add_argument("--disable-backgrounding-occluded-windows")
    browser_opts.add_argument("--disable-features=CalculateNativeWinOcclusion,MojoVideoDecoder")
    browser_opts.add_argument("--disable-blink-features=AutomationControlled")
    browser_opts.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    browser_opts.add_experimental_option("useAutomationExtension", False)
    browser_opts.page_load_strategy = "eager"
    browser_opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36")
    return browser_opts


def initialize_webdriver(run_headless: bool, use_legacy_mode: bool = False) -> webdriver.Chrome:
    driver_service = ChromeService(ChromeDriverManager().install(), log_output=os.devnull)
    web_driver = webdriver.Chrome(service=driver_service, options=configure_browser_options(run_headless, use_legacy_mode))
    web_driver.set_page_load_timeout(40)
    try:
        web_driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
    except Exception:
        pass
    return web_driver


def handle_cookie_consent(web_driver: webdriver.Chrome):
    try:
        consent_btn = WebDriverWait(web_driver, 6).until(EC.presence_of_element_located((By.ID, "onetrust-accept-btn-handler")))
        web_driver.execute_script("arguments[0].click();", consent_btn)
        time.sleep(0.2)
    except TimeoutException:
        pass
    except Exception:
        pass


# =========================== Utilities ===========================
DIGIT_PATTERN = re.compile(r"\d")
AUTHOR_NAME_PATTERN = re.compile(r"[A-Z][A-Za-z''\-]+,\s*(?:[A-Z](?:\.)?)(?:\s*[A-Z](?:\.)?)*", flags=re.UNICODE)
WHITESPACE_PATTERN = re.compile(r"\s+")
PUBLICATION_YEAR_PATTERN = re.compile(r"(19|20)\d{2}")


def _remove_duplicate_strings(string_list: List[str]) -> List[str]:
    seen_items, unique_list = set(), []
    for item in string_list:
        item = item.strip()
        if item and item not in seen_items:
            seen_items.add(item)
            unique_list.append(item)
    return unique_list


def _remove_duplicate_authors(author_objects: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    processed_authors: set[Tuple[str, str]] = set()
    filtered_authors: List[Dict[str, Optional[str]]] = []
    for author_obj in author_objects:
        author_name = (author_obj.get("name") or "").strip()
        author_profile = (author_obj.get("profile") or "").strip() if author_obj.get("profile") else ""
        author_key = (author_name, author_profile)
        if author_name and author_key not in processed_authors:
            processed_authors.add(author_key)
            filtered_authors.append({"name": author_name})
    return filtered_authors


def _validate_person_name(text_input: str) -> bool:
    if not text_input:
        return False
    cleaned_text = text_input.strip()
    invalid_terms = {"profiles", "persons", "people", "overview"}
    if cleaned_text.lower() in invalid_terms:
        return False
    return ((" " in cleaned_text) or ("," in cleaned_text)) and sum(ch.isalpha() for ch in cleaned_text) >= 4


def _parse_publication_year(date_string: str) -> Optional[int]:
    year_match = PUBLICATION_YEAR_PATTERN.search(date_string)
    return int(year_match.group(0)) if year_match else None

# =========================== LISTING (Stage 1) ===========================
def extract_publications_from_page(web_driver: webdriver.Chrome, page_number: int) -> List[Dict]:
    target_url = f"{PUBLICATIONS_BASE_URL}?page={page_number}"
    web_driver.get(target_url)
    handle_cookie_consent(web_driver)
    try:
        WebDriverWait(web_driver, 15).until(
            lambda driver: driver.find_elements(By.CSS_SELECTOR, ".result-container h3.title a")
                      or "No results" in driver.page_source
        )
    except TimeoutException:
        pass

    publication_entries = []
    for container in web_driver.find_elements(By.CLASS_NAME, "result-container"):
        try:
            title_link = container.find_element(By.CSS_SELECTOR, "h3.title a")
            publication_title = title_link.text.strip()
            publication_url = title_link.get_attribute("href")
            if publication_title and publication_url:
                publication_entries.append({"title": publication_title, "link": publication_url})
        except Exception:
            continue
    return publication_entries


def collect_all_publication_links(max_page_limit: int, headless_browsing: bool = False, use_legacy_mode: bool = False) -> List[Dict]:
    web_driver = initialize_webdriver(headless_browsing, use_legacy_mode)
    try:
        web_driver.get(PUBLICATIONS_BASE_URL)
        handle_cookie_consent(web_driver)
        collected_publications: List[Dict] = []
        for page_idx in range(max_page_limit):
            print(f"Processing publication listing page {page_idx + 1} of {max_page_limit}")
            page_publications = extract_publications_from_page(web_driver, page_idx)
            if not page_publications:
                print(f"No publications found on page {page_idx}. Stopping collection process.")
                break
            collected_publications.extend(page_publications)
        unique_publications = {}
        for publication in collected_publications:
            unique_publications[publication["link"]] = publication
        return list(unique_publications.values())
    finally:
        try:
            web_driver.quit()
        except Exception:
            pass


# =========================== DETAIL (Stage 2) ===========================
def _expand_author_sections(web_driver: webdriver.Chrome):
    try:
        for expand_button in web_driver.find_elements(
                By.XPATH,
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'show') or "
                "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more')]"
        )[:2]:
            try:
                web_driver.execute_script("arguments[0].scrollIntoView({block:'center'});", expand_button)
                time.sleep(0.1)
                expand_button.click()
                time.sleep(0.2)
            except Exception:
                continue
    except Exception:
        pass


def _extract_authors_from_navigation_links(web_driver: webdriver.Chrome) -> List[Dict]:
    navigation_y_position = None
    for xpath_selector in [
        "//a[normalize-space()='Overview']",
        "//nav[contains(@class,'tabbed-navigation')]",
        "//div[contains(@class,'navigation') and .//a[contains(.,'Overview')]]",
    ]:
        try:
            navigation_element = web_driver.find_element(By.XPATH, xpath_selector)
            navigation_y_position = navigation_element.location.get("y", None)
            if navigation_y_position:
                break
        except Exception:
            continue
    if navigation_y_position is None:
        navigation_y_position = 900  # fallback

    author_candidates: List[Dict[str, Optional[str]]] = []
    processed_authors = set()
    for author_link in web_driver.find_elements(By.CSS_SELECTOR, "a[href*='/en/persons/']"):
        try:
            link_y_position = author_link.location.get("y", 99999)
            if link_y_position >= navigation_y_position:
                continue
            author_href = (author_link.get_attribute("href") or "").strip()
            try:
                author_name = author_link.find_element(By.CSS_SELECTOR, "span").text.strip()
            except NoSuchElementException:
                author_name = (author_link.text or "").strip()
            if not _validate_person_name(author_name):
                continue
            author_key = (author_name, author_href)
            if author_key in processed_authors:
                continue
            processed_authors.add(author_key)
            author_candidates.append({"name": author_name, "profile": urljoin(web_driver.current_url, author_href)})
        except Exception:
            continue

    return _remove_duplicate_authors(author_candidates)


def _extract_metadata_content(web_driver: webdriver.Chrome, metadata_attributes: List[str]) -> List[str]:
    metadata_values = []
    for attribute_name in metadata_attributes:
        for meta_element in web_driver.find_elements(By.CSS_SELECTOR, f'meta[name="{attribute_name}"], meta[property="{attribute_name}"]'):
            content_value = (meta_element.get_attribute("content") or "").strip()
            if content_value:
                metadata_values.append(content_value)
    return _remove_duplicate_strings(metadata_values)


def _parse_authors_from_json_ld(web_driver: webdriver.Chrome) -> List[str]:
    import json as _json
    author_names = []
    for script_element in web_driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]'):
        script_content = (script_element.get_attribute("textContent") or "").strip()
        if not script_content:
            continue
        try:
            json_data = _json.loads(script_content)
        except Exception:
            continue
        data_objects = json_data if isinstance(json_data, list) else [json_data]
        for data_object in data_objects:
            author_field = data_object.get("author")
            if not author_field:
                continue
            if isinstance(author_field, list):
                for author_item in author_field:
                    name_value = author_item.get("name") if isinstance(author_item, dict) else str(author_item)
                    if name_value: author_names.append(name_value)
            elif isinstance(author_field, dict):
                name_value = author_field.get("name")
                if name_value: author_names.append(name_value)
            elif isinstance(author_field, str):
                author_names.append(author_field)
    return _remove_duplicate_strings(author_names)


def _extract_authors_from_subtitle_text(web_driver: webdriver.Chrome, publication_title: str) -> List[str]:
    try:
        date_element = web_driver.find_element(By.CSS_SELECTOR, "span.date")
    except NoSuchElementException:
        return []
    try:
        subtitle_container = date_element.find_element(By.XPATH, "ancestor::*[contains(@class,'subtitle')][1]")
    except Exception:
        try:
            subtitle_container = date_element.find_element(By.XPATH, "..")
        except Exception:
            subtitle_container = None
    subtitle_text = (subtitle_container.text if subtitle_container else "")
    if publication_title and publication_title in subtitle_text:
        subtitle_text = subtitle_text.replace(publication_title, "")
    subtitle_text = " ".join(subtitle_text.split()).strip()
    digit_match = DIGIT_PATTERN.search(subtitle_text)
    pre_date_text = subtitle_text[:digit_match.start()].strip(" -—–·•,;|") if digit_match else subtitle_text
    pre_date_text = pre_date_text.replace(" & ", ", ").replace(" and ", ", ")
    author_matches = AUTHOR_NAME_PATTERN.findall(pre_date_text)
    return _remove_duplicate_strings(author_matches)


def _convert_names_to_objects(name_list: List[str]) -> List[Dict]:
    return _remove_duplicate_authors([{"name": author_name, "profile": None} for author_name in name_list])


def extract_publication_details(web_driver: webdriver.Chrome, publication_url: str, fallback_title: str) -> Dict:
    web_driver.get(publication_url)
    handle_cookie_consent(web_driver)
    try:
        WebDriverWait(web_driver, 18).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
    except TimeoutException:
        pass

    # Title
    try:
        publication_title = web_driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
    except NoSuchElementException:
        publication_title = fallback_title or ""

    _expand_author_sections(web_driver)

    # AUTHORS
    publication_authors: List[Dict[str, Optional[str]]] = _extract_authors_from_navigation_links(web_driver)
    publication_authors = [author for author in publication_authors if _validate_person_name(author.get("name", ""))]
    if not publication_authors:
        author_name_list = _extract_authors_from_subtitle_text(web_driver, publication_title)
        publication_authors = _convert_names_to_objects(author_name_list)
    if not publication_authors:
        author_name_list = _extract_metadata_content(web_driver, ["citation_author", "dc.contributor", "dc.contributor.author"])
        publication_authors = _convert_names_to_objects(author_name_list)
    if not publication_authors:
        author_name_list = _parse_authors_from_json_ld(web_driver)
        publication_authors = _convert_names_to_objects(author_name_list)

    # PUBLISHED DATE → YEAR
    publication_date_text = None
    for css_selector in ["span.date", "time[datetime]", "time"]:
        try:
            date_element = web_driver.find_element(By.CSS_SELECTOR, css_selector)
            publication_date_text = date_element.get_attribute("datetime") or date_element.text.strip()
            if publication_date_text:
                break
        except NoSuchElementException:
            continue
    if not publication_date_text:
        date_metadata = _extract_metadata_content(web_driver, ["citation_publication_date", "dc.date", "article:published_time"])
        if date_metadata:
            publication_date_text = date_metadata[0]

    publication_year = None
    if publication_date_text:
        year_match = re.search(r"(19|20)\d{2}", publication_date_text)
        if year_match:
            publication_year = int(year_match.group(0))

    # ABSTRACT
    abstract_content = None
    for css_selector in [
        "section#abstract .textblock", "section.abstract .textblock", "div.abstract .textblock",
        "div#abstract", "section#abstract", "div.textblock",
    ]:
        try:
            abstract_element = web_driver.find_element(By.CSS_SELECTOR, css_selector)
            abstract_text = abstract_element.text.strip()
            if abstract_text and len(abstract_text) > 15:
                abstract_content = abstract_text
                break
        except NoSuchElementException:
            continue
    if not abstract_content:
        try:
            for heading_element in web_driver.find_elements(By.CSS_SELECTOR, "h2, h3"):
                if "abstract" in heading_element.text.strip().lower():
                    next_element = heading_element.find_element(By.XPATH, "./following::*[self::div or self::p or self::section][1]")
                    abstract_text = next_element.text.strip()
                    if abstract_text:
                        abstract_content = abstract_text
                        break
        except Exception:
            pass

    return {
        "title": publication_title,
        "year": publication_year,
        "pub_url": publication_url,
        "authors": _remove_duplicate_authors(publication_authors),
        "abstract": abstract_content or ""
    }


# =========================== Workers ===========================
def process_publication_batch(publication_batch: List[Dict], run_headless: bool, use_legacy_mode: bool) -> List[Dict]:
    # batch_driver = initialize_webdriver(headless=run_headless, legacy_headless=use_legacy_mode)
    batch_driver = initialize_webdriver(run_headless=run_headless, use_legacy_mode=use_legacy_mode)
    processed_publications: List[Dict] = []
    try:
        for batch_index, publication_item in enumerate(publication_batch, 1):
            try:
                publication_record = extract_publication_details(batch_driver, publication_item["link"], publication_item.get("title", ""))
                processed_publications.append(publication_record)
                if batch_index % 5 == 0:
                    print(f"Batch processing: {batch_index} of {len(publication_batch)} publications completed")
            except WebDriverException as web_error:
                print(f"Error processing publication {publication_item['link']}: {web_error}")
                continue
    finally:
        try:
            batch_driver.quit()
        except Exception:
            pass
    return processed_publications


def split_into_batches(publication_items: List[Dict], batch_count: int) -> List[List[Dict]]:
    if batch_count <= 1:
        return [publication_items]
    batch_size = ceil(len(publication_items) / batch_count)
    return [publication_items[i:i + batch_size] for i in range(0, len(publication_items), batch_size)]


# =========================== Orchestrator ===========================
def main():
    argument_parser = argparse.ArgumentParser(description="Coventry PurePortal scraper (listing → details, clean author links).")
    argument_parser.add_argument("--outdir", default="data")
    argument_parser.add_argument("--max-pages", type=int, default=50, help="Max listing pages to scan.")
    argument_parser.add_argument("--workers", type=int, default=8, help="Parallel headless browsers for detail pages.")
    argument_parser.add_argument("--listing-headless", action="store_true", help="Run listing headless.")
    argument_parser.add_argument("--legacy-headless", action="store_true", help="Use legacy --headless.")
    parsed_args = argument_parser.parse_args()

    output_directory = Path(parsed_args.outdir)
    output_directory.mkdir(parents=True, exist_ok=True)

    # Stage 1: listing
    print(f"Stage 1: Gathering publication links from up to {parsed_args.max_pages} pages")
    publication_listing = collect_all_publication_links(parsed_args.max_pages, headless_browsing=parsed_args.listing_headless,
                                       use_legacy_mode=parsed_args.legacy_headless)
    if not publication_listing:
        print("No publications discovered during listing collection.", file=sys.stderr)
        return
    (output_directory / "publications_links.json").write_text(json.dumps(publication_listing, indent=2), encoding="utf-8")
    print(f"Stage 1 complete: Found {len(publication_listing)} unique publication links")

    # Stage 2: details
    print(f"Stage 2: Extracting detailed information using {parsed_args.workers} parallel workers")
    publication_batches = split_into_batches(publication_listing, max(1, parsed_args.workers))
    detailed_results: List[Dict] = []
    with ThreadPoolExecutor(max_workers=max(1, parsed_args.workers)) as executor:
        batch_futures = [executor.submit(process_publication_batch, batch, True, parsed_args.legacy_headless) for batch in publication_batches]
        completed_batches = 0
        for future in as_completed(batch_futures):
            batch_results = future.result() or []
            detailed_results.extend(batch_results)
            completed_batches += 1
            print(f"Stage 2 progress: {completed_batches} of {len(publication_batches)} batches completed (added {len(batch_results)} publications)")

    # Save JSONL
    output_file_path = output_directory / "publications.jsonl"
    with output_file_path.open("w", encoding="utf-8") as output_file:
        for publication_record in detailed_results:
            json.dump(publication_record, output_file, ensure_ascii=False)
            output_file.write("\n")
    print(f"Process complete: Saved {len(detailed_results)} publication records to {output_file_path}")


if __name__ == "__main__":
    main()