"""
Invoice Downloader Orchestrator
CLI tool to download invoices from multiple vendors

Usage:
    python orchestrator.py [vendor] [account_index]
    python orchestrator.py rogers 1

Last Modified: 12/2/2025
"""

import os
import sys

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load Integrations
from ITC.integrations.email_notifier import send_invoice_email

# Load Vendor Downloaders
from ITC.downloaders.rogers import RogersDownloader
from ITC.downloaders.enmax import EnmaxDownloader
from ITC.downloaders.eastward import EastwardDownloader
from ITC.downloaders.mhydro import ManitobaHydroDownloader


# Future vendors:

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# CONFIGURATION
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

# Load environment variables
load_dotenv()

# Get download path from .env
DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH')

# Validate DOWNLOAD_PATH is set
if not DOWNLOAD_PATH:
    print(" Error: DOWNLOAD_PATH must be set in .env file")

# Map vendor names to their downloader classes
VENDORS ={
    'rogers': RogersDownloader(),
    'enmax': EnmaxDownloader(),
    'eastward': EastwardDownloader(),
    'mhydro': ManitobaHydroDownloader()
    # Append with future vendors
}


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# HELPER FUNCTIONS
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def print_banner():
    """ Print a nice banner for the CLI """
    print("="*70)
    print("            INVOICE DOWNLOADER ORCHESTRATOR")
    print("="*70)
    print()

def print_usage():
    """ Print usage instructions """
    print("Usage: python orchestrator.py <vendor> <account_index>")
    print()
    print("Available vendors:")
    for vendor_name, downloader in VENDORS.items():
        print(f" - {vendor_name} (accounts: 0-{downloader.max_accounts - 1})")
    print()


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# MAIN FUNCTION
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def main():
    """ Main orchestrator function """
    print_banner()

    #  Check command line arguments
    if len(sys.argv) != 3:
        print(" Error: Invalid number of arguments")
        print()
        print_usage()
        sys.exit(1)

    vendor_name = sys.argv[1].lower()

    # Validate account index is a number
    try:
        account_index = int(sys.argv[2])
    except ValueError:
        print(f" Error: Account index must be a number, got '{sys.argv[2]}'")
        print()
        print_usage()
        sys.exit(1)

    # Check if vendor exists
    if vendor_name not in VENDORS:
        print(f" Error: Unknown vendor '{vendor_name}")
        print(f" Available vendors: {', '.join(VENDORS.keys())}")
        print()
        print_usage()
        sys.exit(1)

    # Get the downloader for this vendor
    downloader = VENDORS[vendor_name]

    # Validate account index within range
    if not 0 <= account_index < downloader.max_accounts:
        print(f" Error: Account index must be 0-{downloader.max_accounts - 1} for {vendor_name}")
        print(f" You provided: {account_index}")
        print()
        print_usage()
        sys.exit(1)

    # Print execution info
    print(f" Starting download for {vendor_name.upper()}")
    print(f" Account: #{account_index + 1}")
    print(f" Download path: {DOWNLOAD_PATH}")
    print(f" Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}")
    print("-"*70)
    print()

    # Run the download
    try:
        download_file_path = downloader.run(
            account_index=account_index,
            download_path=DOWNLOAD_PATH,
            headless=False # Set to True for production/background runs
        )

        print()
        print("="*70)

        if download_file_path: # Checks if we got a valid path back
            print(f" SUCCESS: Downloaded invoice for {vendor_name.upper()} account #{account_index + 1}")

            # Convert to path object
            latest_file = Path(download_file_path)

            print(f"DEBUG: File to email: {latest_file}")

            # Send email (ONLY if download was successful)
            print()
            print("Sending email...")
            email_sent = send_invoice_email(latest_file)

            if email_sent:
                print("✅ Email sent successfully!")
            else:
                print("❌ Email failed to send.")

        else:
            # Download failed - NO EMAIL SENT
            print(f" ERROR: Download failed for {vendor_name.upper()} account #{account_index + 1}")
            print(" No email sent (download unsuccessful)")

        print()
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

        sys.exit(0 if download_file_path else 1)
    
    except Exception as e:
        print()
        print("="*70)
        print(f"CRITICAL ERROR: {e}")
        print("="*70)
        print(" No email sent (error occurred)")
        sys.exit(1)


if __name__ == "__main__":
     main()