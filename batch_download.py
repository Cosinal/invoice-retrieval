"""
Batch Invoice Downloader (Test Script)
Downloads ALL accounts for Rogers, Manitoba Hydro, and Halifax Water
Runs headless and prints progress [k/n]

Usage:
    python batch_download.py

Last Modified: 12/17/2025
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from ITC.integrations.email_notifier import send_invoice_email

from ITC.downloaders.rogers import RogersDownloader
from ITC.downloaders.mhydro import ManitobaHydroDownloader
from ITC.downloaders.halifaxwater import HalifaxWaterDownloader

def build_jobs(downloaders: dict[str, object]):
    """
    Returns a list of jobs: [(vendor_name, downloader_instance, account_index), ...]
    """

    jobs = []

    for vendor_name, d1 in downloaders.items():
        for account_index in range(d1.max_accounts):
            jobs.append((vendor_name, d1, account_index))
    return jobs


def main():
    load_dotenv()

    download_path = os.getenv("DOWNLOAD_PATH")
    if not download_path:
        raise ValueError("DOWNLOAD_PATH must be set in the .env")
    
    # Insantiate downloaders once (ok if they don't keep browser state between run() calls)
    downloaders = {
        "rogers": RogersDownloader(),
        "mhydro": ManitobaHydroDownloader(),
        "hwater": HalifaxWaterDownloader()
    }

    jobs = build_jobs(downloaders)
    total = len(jobs)

    ok_count = 0
    fail_count = 0

    print("=" * 70)
    print("BATCH INVOICE DOWNLOADER")
    print("Vendors: Rogers, Manitoba Hydro, and Halifax Water")
    print(f"Download path: {download_path}")
    print(f"Total jobs: {total}")
    print("=" * 70)

    for i, (vendor_name, downloader, account_index) in enumerate(jobs, start=1):
        prefix = f"[{i}/{total}]"
        human_account = account_index + 1

        print(f"\n{prefix} {vendor_name.upper()} - account #{human_account}")

        try:
            file_path = downloader.run(
                account_index = account_index,
                download_path = download_path,
                headless = True
            )

            if not file_path:
                print(f"{prefix}: Download failed (no email)")
                fail_count += 1
                continue

            f = Path(file_path)
            print(f"{prefix} Downloaded: {f.name}")

            print(f"{prefix} Sending email...")
            if send_invoice_email(f):
                print(f"{prefix} Email Sent")
                ok_count += 1

            else:
                print(f"{prefix} Email failed")
                fail_count += 1
        
        except Exception as e:
            print(f"{prefix} Error: {e}")
            fail_count += 1

    print("\n" + "=" * 70)
    print(f"Done. Successful: {ok_count} | Failed: {fail_count} | Total: {total}")
    print("=" * 70)

if __name__ == "__main__":
    main()

