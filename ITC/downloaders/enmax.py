"""
Enmax Invoice Downloader
Implements Enmax-specific login and download logic

Last Modified: 12/10/2025
"""

import os
import random
from pathlib import Path 
from datetime import datetime
from dotenv import load_dotenv

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from .base import VendorDownloader

class EnmaxDownloader(VendorDownloader):
    """
    Enmax-specific downloader implementation
    """

    # Account metadata for filename generation
    ACCOUNT_METADATA = {
        0: {'vendor_number': 'ENMA01', 'account_number': '4193', 'gl_account':'68000-YYC-18-410'},
        1: {'vendor_number': 'ENMA01', 'account_number': '1303', 'gl_account':'61202-YYC-11-412'},
        2: {'vendor_number': 'ENMA01', 'account_number': '2173', 'gl_account':'68000-YYC-18-410'},
        3: {'vendor_number': 'ENMA01', 'account_number': '3673', 'gl_account':'68000-YYC-10-410'},
        4: {'vendor_number': 'ENMA01', 'account_number': '2573', 'gl_account':'68002-YYC-11-412'}
    }

    # Vendor metadata for pdf parsing
    VENDOR_METADATA = {
        'data_bbox': (0, 0, 0, 0), # TODO: Find with bbox_finder.py
        'date_format': '%b %d, %Y' # TODO: Verify this is the format on Enmax invoices
    }

    def __init__(self):
        super().__init__(vendor_name='enmax', max_accounts=5)

        # Load environment variables
        load_dotenv()

        # Enmax-specific credentials
        self.login_url = os.getenv('ENMAX_LOGIN_URL')
        self.username = os.getenv('ENMAX_USERNAME')
        self.password = os.getenv('ENMAX_PASSWORD')

        # Validate credentials
        if not all([self.login_url, self.username, self.password]):
            raise ValueError("Enmax credentials not configured in .env file")
        
    def login(self, account_index):
        """
        Enmax-specific login implementation
        """

        self.logger.info("Logging in to Enmax portal")
        self.logger.info(f"Using username: {self.username}")
        self.logger.info(f"Navigating to login URL: {self.login_url}")

        # Navigate to login page
        self.page.goto(self.login_url, wait_until='domcontentloaded', timeout=60000)

        # Random human-like delay
        self.page.wait_for_timeout(random.randint(1000, 3000))
        self.take_screenshot("01_login_page")

        try:

            # Fill username
            self.page.wait_for_selector('#username', state='visible', timeout=10000)
            self.page.fill('#username', '')
            self.page.type('#username', self.username, delay=random.randint(100, 200))
            self.logger.debug("Entered username")
            self.page.wait_for_timeout(1000)

            # Fill password
            self.page.wait_for_selector('#current-password', state='visible', timeout=10000)
            self.page.type('#current-password', self.password, delay=random.randint(100, 200))
            self.logger.debug("Entered password")
            self.page.wait_for_timeout(1000)

            # Click Sign-In button
            sign_in_button = '#js-subscription-form > div > button'
            self.page.click(sign_in_button, force=True)
            self.logger.debug("Clicked Sign-In button")

            # Wait for login to complete
            # TODO: Replace this with the actual selector of an element that appears after login
            self.page.wait_for_timeout(5000) # Temporary wait

            self.take_screenshot("02_post_login")
            self.logger.info("Login successful")

        except PlaywrightTimeout as e:
            self.logger.error(f"Login timeout: {e}")
            self.take_screenshot("error_login_timeout")
            raise

        except Exception as e:
            self.logger.error(f"Loggin failed: {e}", exc_info=True)
            self.take_screenshot("error_login_failed")
            raise


    def navigate_to_invoices(self, account_index):
        """
        Enmax-specific navigation to invoices page
        """

        self.logger.info(f"Navigating to invoices for account #{account_index + 1}")

        # TODO: Implement Enmax navigation to invoices
        pass

    def download_invoice(self, account_index):
        """
        Enmax-specific invoice download implementation
        """

        self.logger.info(f"Downloading invoice for account #{account_index + 1}")

        #TODO: Implement Enmax invoice download
        pass