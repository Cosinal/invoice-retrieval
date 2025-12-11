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
        Start frpm homepage to avoid bot detection
        """

        homepage_url = "https://www.enmax.com/"
        self.logger.info(f"Starting at Enmax homepage: {homepage_url}")

        try:
            # Navigate to homepage first
            self.page.goto(homepage_url, wait_until="domcontentloaded", timeout = 30000)
            self.page.wait_for_timeout(random.randint(2000, 4000))
            self.take_screenshot('01_homepage')

            # Click "Sign-In" button in top right
            sign_in_button_selector = '#header > div.header_header__gO7fM > div.relative.w-full.bg-white.py-6.lg\:py-0.lg\:pt-6.lg\:px-20.lg\:pb-6 > div.w-full.hidden.lg\:flex.justify-between.items-center.m-auto.max-w-inner-content.gap-12 > div.header_right_content__iyUZ9 > a'
            
            self.page.wait_for_selector(sign_in_button_selector, state='visible', timeout=10000)
            self.page.click(sign_in_button_selector)
            self.logger.info("Clicked Sign-In Button")

            # Wait for login page to load
            username_selector = '#username'
            self.page.wait_for_selector(username_selector, state='visible', timeout=30000)

            # Enter Username
            self.page.wait_for_timeout(random.randint(1000, 4000))

            self.page.click(username_selector)
            self.page.type(username_selector, self.username, delay = random.randint(100, 250))
            self.logger.debug(f"Username Entered: {self.username}")

            # Navigate and Enter Password
            self.page.wait_for_timeout(random.randint(500, 1000))
            self.page.keyboard.press('Tab')
            self.page.wait_for_timeout(random.randint(300, 670))

            self.page.type('#current-password', self.password, delay = random.randint(67, 250))
            self.logger.debug("Entered Password")
            self.page.wait_for_timeout(67000)

            # Navigate and Finalize login
            






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