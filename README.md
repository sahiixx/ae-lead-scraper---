# UAE Lead Scraper

Automated web scraper for Dubai real estate leads from Dubizzle. Extracts owner-direct listings with phone numbers and saves to Google Sheets.

## Features

- Scrapes multiple Dubai communities (Springs, Arabian Ranches 3, Al Waha)
- Extracts UAE phone numbers and normalizes to international format
- Identifies owner-direct listings (no agent/commission)
- Flags "hot deals" (cheap + owner-direct)
- Auto-uploads to Google Sheets with WhatsApp links
- Runs every 6 hours via cloud deployment
- Retry logic and rate limiting to avoid blocks
- CSV backup files for each community

## Quick Start

### 1. Set Up Google Sheets

1. Create a new Google Sheet
2. Copy the Sheet ID from URL: `docs.google.com/spreadsheets/d/[SHEET_ID]/edit`

### 2. Create Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: `uae-scraper`
3. Enable APIs:
   - Google Sheets API
   - Google Drive API
4. Create Service Account:
   - IAM & Admin → Service Accounts → Create
   - Name: `scraper-bot`
   - Create JSON key and download
5. Share your Google Sheet with the service account email (Editor access)

### 3. Deploy

#### Option A: GitHub Actions (Free)

1. Go to repo Settings → Secrets → Actions
2. Add secrets:
   - `SHEET_ID`: Your Google Sheet ID
   - `GOOGLE_CREDENTIALS`: Full JSON key file contents
3. Go to Actions → Run workflow manually

#### Option B: Render ($7/month)

1. Connect repo at [render.com](https://render.com)
2. Select "Blueprint" deployment
3. Add environment variables:
   - `SHEET_ID`
   - `GOOGLE_CREDENTIALS`

### 4. Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Test connection
python test_setup.py

# Run scraper
python scraper.py
```

## Configuration

Edit `scraper.py` to customize:

```python
# Communities to scrape (add/remove as needed)
communities = [
    ('Springs', 'https://dubai.dubizzle.com/...'),
    ('AR3', 'https://dubai.dubizzle.com/...'),
]

# Hot deal threshold (AED/year)
is_hot = price_num < 140000 and is_owner
```

## Output

### Google Sheets Columns

| Column | Description |
|--------|-------------|
| Community | Area name |
| Title | Listing title |
| Price | Rental price |
| Phones | Extracted phone numbers |
| Is Owner | YES/NO owner-direct |
| WhatsApp | Click-to-chat link |
| Scraped At | Timestamp |
| Hot Deal | YES/NO flag |

### CSV Files

Each run creates backup files:
- `Springs_leads.csv`
- `AR3_leads.csv`
- `Al_Waha_leads.csv`

## Schedule

- **GitHub Actions**: Every 6 hours (0:00, 6:00, 12:00, 18:00 UTC)
- **Render**: Every 6 hours

To change schedule, edit `.github/workflows/scraper.yml`:
```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
  - cron: '0 */2 * * *'  # Every 2 hours
  - cron: '0 8,20 * * *' # 8am and 8pm only
```

## Troubleshooting

### "GOOGLE_CREDENTIALS not set"
- Check your environment variables are properly set
- For GitHub: Settings → Secrets → Actions
- For Render: Environment tab

### "Permission denied"
- Share your Google Sheet with the service account email
- The email is in your JSON file under `client_email`

### "No listings found"
- Dubizzle may have changed their HTML structure
- Check if the URLs are still valid
- Try running locally to debug

## License

MIT
