#!/usr/bin/env python3
"""
UAE Lead Scraper - Scrapes Dubai real estate listings from Dubizzle
and saves owner-direct leads to Google Sheets.
"""

import os
import json
import re
import time
import random
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from oauth2client.service_account import ServiceAccountCredentials


class DubaiCloudScraper:
    def __init__(self):
        self.client = None
        self.sheet = None
        self.driver = None
        self.setup_sheets()
        self.setup_driver()

    def setup_sheets(self):
        """Initialize Google Sheets connection."""
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

        creds_str = os.getenv('GOOGLE_CREDENTIALS')
        if not creds_str:
            raise ValueError("GOOGLE_CREDENTIALS environment variable not set")

        sheet_id = os.getenv('SHEET_ID')
        if not sheet_id:
            raise ValueError("SHEET_ID environment variable not set")

        try:
            creds_json = json.loads(creds_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in GOOGLE_CREDENTIALS: {e}")

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(sheet_id).sheet1
        print("Connected to Google Sheets successfully")

    def setup_driver(self):
        """Initialize Selenium WebDriver with Chrome."""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome WebDriver initialized successfully")
        except WebDriverException as e:
            raise RuntimeError(f"Failed to initialize Chrome WebDriver: {e}")

    def normalize_phone(self, phone):
        """Normalize UAE phone number to international format."""
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)

        # Handle various formats
        if digits.startswith('971'):
            return digits
        elif digits.startswith('0'):
            return '971' + digits[1:]
        elif digits.startswith('5'):
            return '971' + digits
        elif len(digits) == 9 and digits[0] == '5':
            return '971' + digits

        return digits

    def extract_phones(self, text):
        """Extract UAE mobile phone numbers from text."""
        # UAE mobile patterns (05X XXX XXXX)
        patterns = [
            r'\+971\s*5[0-9]\s*\d{3}\s*\d{4}',
            r'00971\s*5[0-9]\s*\d{3}\s*\d{4}',
            r'971\s*5[0-9]\s*\d{3}\s*\d{4}',
            r'05[0-9][\s-]?\d{3}[\s-]?\d{4}',
            r'5[0-9]\s*\d{3}\s*\d{4}',
        ]

        phones = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                normalized = self.normalize_phone(match)
                # Validate: should be 12 digits starting with 9715
                if len(normalized) == 12 and normalized.startswith('9715'):
                    phones.add(normalized)

        return list(phones)

    def is_owner_listing(self, text):
        """Check if listing appears to be owner-direct."""
        owner_keywords = [
            'owner', 'direct', 'no commission', 'landlord',
            'direct from owner', 'owner direct', 'no agent',
            'private', 'مالك', 'بدون عمولة'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in owner_keywords)

    def scrape_dubizzle_community(self, name, url, max_retries=3):
        """Scrape listings from a Dubizzle community page."""
        print(f"\nScraping {name}...")

        for attempt in range(max_retries):
            try:
                self.driver.get(url)

                # Random delay to avoid detection
                time.sleep(random.uniform(2, 4))

                wait = WebDriverWait(self.driver, 15)

                # Wait for listings to load
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-testid='listing-card'], .listing-card, article")
                ))

                # Try multiple selectors for listing cards
                selectors = [
                    "[data-testid='listing-card']",
                    ".listing-card",
                    "article[data-listing]",
                    ".sc-listing-card"
                ]

                cards = []
                for selector in selectors:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        break

                if not cards:
                    print(f"  No listings found for {name}")
                    return []

                print(f"  Found {len(cards)} listings")
                cards = cards[:20]  # Limit to first 20

                leads = []
                for i, card in enumerate(cards):
                    try:
                        card_text = card.text

                        # Try to get title
                        title = ""
                        for title_sel in ['h2', 'h3', '[data-testid="title"]', '.title']:
                            try:
                                title_elem = card.find_element(By.CSS_SELECTOR, title_sel)
                                title = title_elem.text.strip()
                                if title:
                                    break
                            except NoSuchElementException:
                                continue

                        # Try to get price
                        price = ""
                        for price_sel in ['[data-testid="price"]', '.price', '.amount']:
                            try:
                                price_elem = card.find_element(By.CSS_SELECTOR, price_sel)
                                price = price_elem.text.strip()
                                if price:
                                    break
                            except NoSuchElementException:
                                continue

                        # Extract phone numbers
                        phones = self.extract_phones(card_text)

                        if not phones:
                            continue

                        # Check if owner listing
                        is_owner = self.is_owner_listing(card_text)

                        # Parse price for comparison
                        price_num = 0
                        price_match = re.search(r'[\d,]+', price.replace(',', ''))
                        if price_match:
                            try:
                                price_num = int(price_match.group().replace(',', ''))
                            except ValueError:
                                pass

                        # Hot deal: cheap + owner
                        is_hot = price_num > 0 and price_num < 140000 and is_owner

                        leads.append({
                            'community': name,
                            'title': title[:100] if title else 'No title',
                            'price': price or 'N/A',
                            'price_num': price_num,
                            'phones': ', '.join(phones),
                            'is_owner': 'YES' if is_owner else 'NO',
                            'whatsapp': f"https://wa.me/{phones[0]}",
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'hot_deal': 'YES' if is_hot else 'NO'
                        })

                    except Exception as e:
                        print(f"  Error parsing listing {i+1}: {e}")
                        continue

                print(f"  Extracted {len(leads)} leads with phone numbers")
                return leads

            except TimeoutException:
                print(f"  Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue

            except WebDriverException as e:
                print(f"  WebDriver error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue

        print(f"  Failed to scrape {name} after {max_retries} attempts")
        return []

    def save_to_sheets(self, leads):
        """Save leads to Google Sheets."""
        if not leads:
            print("\nNo leads to save")
            return

        print(f"\nSaving {len(leads)} leads to Google Sheets...")

        # Check if headers exist
        try:
            headers = self.sheet.row_values(1)
            if not headers:
                self.sheet.append_row([
                    'Community', 'Title', 'Price', 'Phones',
                    'Is Owner', 'WhatsApp', 'Scraped At', 'Hot Deal'
                ])
        except Exception:
            self.sheet.append_row([
                'Community', 'Title', 'Price', 'Phones',
                'Is Owner', 'WhatsApp', 'Scraped At', 'Hot Deal'
            ])

        # Batch append for efficiency
        rows = []
        for lead in leads:
            rows.append([
                lead['community'],
                lead['title'],
                lead['price'],
                lead['phones'],
                lead['is_owner'],
                lead['whatsapp'],
                lead['scraped_at'],
                lead['hot_deal']
            ])

        # Append in batches of 10 to avoid rate limits
        for i in range(0, len(rows), 10):
            batch = rows[i:i+10]
            for row in batch:
                try:
                    self.sheet.append_row(row)
                except Exception as e:
                    print(f"  Error appending row: {e}")
            time.sleep(1)  # Rate limit protection

        print(f"Saved {len(leads)} leads to Google Sheets")

        # Report hot deals
        hot_deals = [l for l in leads if l['hot_deal'] == 'YES']
        if hot_deals:
            print(f"\n*** {len(hot_deals)} HOT DEALS FOUND! ***")
            for h in hot_deals[:5]:
                print(f"  - {h['community']}: {h['title'][:40]} | {h['price']} | {h['phones']}")

    def run(self):
        """Main execution method."""
        communities = [
            ('Springs', 'https://dubai.dubizzle.com/en/property-for-rent/residential/villahouse/in/the-springs/'),
            ('AR3', 'https://dubai.dubizzle.com/en/property-for-rent/residential/villahouse/in/arabian-ranches-3/'),
            ('Al_Waha', 'https://dubai.dubizzle.com/en/property-for-rent/residential/villahouse/in/al-waha/')
        ]

        print(f"Starting scrape at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Communities to scrape: {len(communities)}")

        all_leads = []
        for name, url in communities:
            try:
                leads = self.scrape_dubizzle_community(name, url)
                all_leads.extend(leads)

                # Save individual CSV backup
                if leads:
                    df = pd.DataFrame(leads)
                    df.to_csv(f'{name}_leads.csv', index=False)
                    print(f"  Saved {name}_leads.csv")

                # Delay between communities
                time.sleep(random.uniform(3, 6))

            except Exception as e:
                print(f"Error scraping {name}: {e}")
                continue

        # Save all to sheets
        self.save_to_sheets(all_leads)

        # Cleanup
        if self.driver:
            self.driver.quit()

        # Summary
        print(f"\n{'='*50}")
        print(f"SCRAPE COMPLETE")
        print(f"{'='*50}")
        print(f"Total leads captured: {len(all_leads)}")
        print(f"Owner-direct leads: {sum(1 for l in all_leads if l['is_owner'] == 'YES')}")
        print(f"Hot deals: {sum(1 for l in all_leads if l['hot_deal'] == 'YES')}")
        print(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    try:
        scraper = DubaiCloudScraper()
        scraper.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        raise
