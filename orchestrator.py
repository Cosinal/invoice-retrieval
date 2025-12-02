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

from ITC.downloaders.rogers import RogersDownloader
# Future vendors:
# from ITC.downloaders.bell import BellDownloader

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
    'rogers': RogersDownloader()
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
        success = downloader.run(
            account_index=account_index,
            download_path=DOWNLOAD_PATH,
            headless=False # Set to True for production/background runs
        )

        print()
        print("="*70)

        if success:
            print("Success!")
        else:
            print("Failed :(")

        sys.exit(0 if success else 1)

    except Exception as e:
        print()
        print("="*70)
        print(f"CRITICAL ERROR: {e}")
        print("="*70)
        sys.exit(1)

if __name__ == "__main__":
    main()


