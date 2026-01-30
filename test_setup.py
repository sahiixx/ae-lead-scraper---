#!/usr/bin/env python3
"""
Test script to verify Google Sheets connection works.
Run this locally before deploying to cloud.

Usage:
1. Create a .env file with SHEET_ID and GOOGLE_CREDENTIALS
2. Run: python test_setup.py
"""

import os
import json
import sys

try:
    from dotenv import load_dotenv
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    print("Missing dependencies. Run: pip install -r requirements.txt")
    sys.exit(1)

load_dotenv()

def test_connection():
    print("Testing Google Sheets connection...\n")

    # Check environment variables
    sheet_id = os.getenv('SHEET_ID')
    creds_str = os.getenv('GOOGLE_CREDENTIALS')

    if not sheet_id:
        print("ERROR: SHEET_ID not found in environment")
        print("  Add it to your .env file: SHEET_ID=your_sheet_id_here")
        return False
    print(f"SHEET_ID: {sheet_id[:10]}...{sheet_id[-5:]}")

    if not creds_str:
        print("ERROR: GOOGLE_CREDENTIALS not found in environment")
        print("  Add the full JSON to your .env file")
        return False

    try:
        creds_json = json.loads(creds_str)
        print(f"Service Account: {creds_json.get('client_email', 'NOT FOUND')}")
    except json.JSONDecodeError:
        print("ERROR: GOOGLE_CREDENTIALS is not valid JSON")
        return False

    # Try to connect
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        print("Authorized with Google successfully")
    except Exception as e:
        print(f"ERROR: Failed to authorize: {e}")
        return False

    # Try to open sheet
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        print(f"Opened sheet: {sheet.title}")

        # Check headers
        headers = sheet.row_values(1)
        if headers:
            print(f"Headers found: {headers}")
        else:
            print("Sheet is empty - adding headers...")
            sheet.append_row(['Community', 'Title', 'Price', 'Phones', 'Is Owner', 'WhatsApp', 'Scraped At', 'Hot Deal'])
            print("Headers added!")

    except gspread.exceptions.SpreadsheetNotFound:
        print("ERROR: Sheet not found. Check your SHEET_ID")
        return False
    except gspread.exceptions.APIError as e:
        if 'PERMISSION_DENIED' in str(e):
            print("ERROR: Permission denied. Share the sheet with your service account email:")
            print(f"  {creds_json.get('client_email')}")
        else:
            print(f"ERROR: API error: {e}")
        return False

    print("\nSUCCESS! Your setup is working correctly.")
    print("You can now deploy to Render or GitHub Actions.")
    return True

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
