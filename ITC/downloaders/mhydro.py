"""
Manitoba Hydro Invoice Downloader
Implements Manitoba Hydro-specific login and download logic

Last Modified: 12/11/2025
"""

import os
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from .base import VendorDownloader

class ManitobaHydroDownloader(VendorDownloader):
    """ Manitoba Hydro - specific Invoice Downloader """

    # Account Metadata for filename generation
    ACCOUNT_METADATA = {
        0: {'vendor_number': 'MANI03', 'account_number': '7950', 'gl_account': '68100-YWG-10-410'}
    }

    # Vendor metadata for pdfparsing
    VENDOR_METADATA = {
        'data_bbox': (0, 0, 0, 0), # will adjust later
        'date_format': '%b %d, %Y'
    }

    def __init__(self):
        super().__init__(vendor_name='mhydro', max_accounts=1) 

        # Load environment variables
        load_dotenv()

        # Manitoba Hydro - specific config
        self.login_url = os.getenv('MHYDRO_LOGIN_URL')
        self.username = os.getenv('MHYDRO_USERNAME')
        self.password = os.getenv('MHYDRO_PASSWORD')

        # Validate
        if not all ([self.login_url, self.username, self.password]):
            raise ValueError("Manitoba Hydro variables need to be set in .env")
        
    def login(self, account_index):
        """
        Manitoba Hydro - specific login flow
        Note: account_index is not used (only one account) but enabled for future scale
        """

        # Navigate to website
        self.logger.info(f"Navigating to {self.login_url}")
        self.page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)

        # Random human-like delay
        self.page.wait_for_timeout(random.randint(1000, 3000))
        self.take_screenshot('01_login_page')

        try:
            # Selectors
            username_selector = '#txtLogin'
            password_selector = '#txtpwd'
            sign_in_selector = '#btnlogin'

            # Navigate and Enter Username
            self.page.wait_for_selector(username_selector, state='visible', timeout=10000)
            self.page.type(username_selector, self.username, delay = random.randint(100, 300))
            self.logger.debug(f"Username entered: {self.username}")
            self.page.wait_for_timeout(1000)

            # Navigate and Enter Password
            self.page.wait_for_selector(username_selector, state='visible', timeout=10000)
            self.page.type(password_selector, self.password, delay = random.randint(100, 300))
            self.logger.debug("Password Entered!")
            self.page.wait_for_timeout(1000)

            # Click Sign In Button
            self.page.click(sign_in_selector)
            self.logger.info("Sign In Button Clicked!")

            # Waut for View Bill sector 
            view_bill_selector = '#ContentPlaceHolder1_BillingUserControl_spn_ViewBill > div > a'
            self.page.wait_for_selector(
                view_bill_selector,
                state='visible',
                timeout=20000
            )

            self.take_screenshot('02_after_login')

        except PlaywrightTimeout as e:
            self.logger.error(f"Login timeout: {e}")
            self.take_screenshot('error_login_timeout')
            raise

        except Exception as e:
            self.logger.error(f"Login failed: {e}", exc_info=True)
            self.take_screenshot('error_login_failed')
            raise


    def navigate_to_invoices(self, account_index):
        """
        Eastward-specific navigation to invoices page
        """

        self.logger.info(f"Navigating to invoices for account #{account_index + 1}")

        # TODO: Implement Eastward navigation to invoices
        pass

    def download_invoice(self, account_index):
        """
        Eastward-specific invoice download implementation
        """

        self.logger.info(f"Downloading invoice for account #{account_index + 1}")

        #TODO: Implement Eastward invoice download
        pass