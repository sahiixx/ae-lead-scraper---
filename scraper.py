import os
import json
import re
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class DubaiCloudScraper:
    def __init__(self):
        self.setup_sheets()
        self.setup_driver()

    def setup_sheets(self):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_json = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(os.getenv('SHEET_ID')).sheet1

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def scrape_dubizzle_community(self, name, url):
        print(f"Scraping {name}...")
        self.driver.get(url)
        wait = WebDriverWait(self.driver, 10)

        # Wait for listings to load
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='listing-card']")))

        cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='listing-card']")[:20]

        leads = []
        for card in cards:
            try:
                title = card.find_element(By.CSS_SELECTOR, "h2").text
                price = card.find_element(By.CSS_SELECTOR, "[data-testid='price']").text
                desc = card.text

                # Extract phones
                phones = re.findall(r'(?:\+971|0)?\s*5[0-6]\s*\d{3}\s*\d{4}', desc)
                phones = list(set([p.replace(' ', '').replace('+971', '').replace('0', '971', 1) for p in phones]))

                is_owner = any(k in desc.lower() for k in ['owner', 'direct', 'no commission', 'landlord'])

                if phones:
                    price_num = int(re.sub(r'[^\d]', '', price)) if re.search(r'\d', price) else 0

                    leads.append({
                        'community': name,
                        'title': title[:100],
                        'price': price,
                        'price_num': price_num,
                        'phones': ', '.join(phones),
                        'is_owner': 'YES' if is_owner else 'NO',
                        'whatsapp': f"https://wa.me/{phones[0]}",
                        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'hot_deal': 'YES' if (price_num < 140000 and is_owner) else 'NO'
                    })
            except:
                continue

        return leads

    def save_to_sheets(self, leads):
        if not leads:
            print("No leads found")
            return

        # Append to Google Sheet
        for lead in leads:
            row = [lead['community'], lead['title'], lead['price'], lead['phones'],
                   lead['is_owner'], lead['whatsapp'], lead['scraped_at'], lead['hot_deal']]
            self.sheet.append_row(row)

        print(f"Saved {len(leads)} leads to Google Sheets")

        # Hot deals alert
        hot = [l for l in leads if l['hot_deal'] == 'YES']
        if hot:
            print(f"{len(hot)} HOT DEALS FOUND!")
            for h in hot[:3]:
                print(f"   {h['title'][:50]} - {h['price']} - {h['phones']}")

    def run(self):
        communities = [
            ('Springs', 'https://dubai.dubizzle.com/en/property-for-rent/residential/villahouse/in/the-springs/64326/'),
            ('AR3', 'https://dubai.dubizzle.com/en/property-for-rent/residential/villahouse/in/arabian-ranches-3/62583/'),
            ('Al_Waha', 'https://dubai.dubizzle.com/en/property-for-rent/residential/villahouse/in/al-waha/62069/')
        ]

        all_leads = []
        for name, url in communities:
            try:
                leads = self.scrape_dubizzle_community(name, url)
                all_leads.extend(leads)
                pd.DataFrame(leads).to_csv(f'{name}_leads.csv', index=False)
            except Exception as e:
                print(f"Error scraping {name}: {e}")

        self.save_to_sheets(all_leads)
        self.driver.quit()
        print(f"\nTOTAL: {len(all_leads)} owner leads captured")

if __name__ == "__main__":
    scraper = DubaiCloudScraper()
    scraper.run()
