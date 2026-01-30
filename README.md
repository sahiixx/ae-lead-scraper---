# UAE Lead Scraper

Automated web scraper for Dubai real estate leads from Dubizzle.

## Features
- Scrapes multiple Dubai communities automatically
- Extracts phone numbers and identifies owner-direct listings
- Auto-uploads leads to Google Sheets
- Flags hot deals (cheap + owner-direct)
- Runs every 6 hours via cloud deployment

## Deployment Options

### Option 1: Render (Recommended - $7/month)
1. Push this repo to GitHub
2. Go to render.com → New → Blueprint
3. Connect your GitHub repo
4. Add environment variables:
   - `SHEET_ID`: Your Google Sheet ID
   - `GOOGLE_CREDENTIALS`: Your service account JSON

### Option 2: GitHub Actions (Free)
1. Go to Settings → Secrets
2. Add `SHEET_ID` and `GOOGLE_CREDENTIALS`
3. Workflow runs automatically every 6 hours

## Setup

### Get Google Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a service account
3. Download the JSON key file
4. Share your Google Sheet with the service account email

### Installation (Local Testing)
```bash
pip install -r requirements.txt
python scraper.py
```

## Configuration
Edit `scraper.py` to change:
- Communities to scrape
- Price threshold for "hot deals"
- Scraping schedule

## Results
Data is automatically saved to:
- Google Sheets (live)
- CSV files (local backup)
