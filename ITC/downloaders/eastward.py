"""
Eastward Energy Invoice Downloader
Implements Eastward Energy - specific login and download logic

Last Modified: 12/11/2025


EASTWARD HAS 2FA SO IT IS NOT AUTOMATABLE UNTIL 2FA IS REDIRECTED
TO AN EMAIL THE PROGRAM CAN SEE. Otherwise, should be extremely easy to automate
"""

import os
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from .base import VendorDownloader

class EastwardDownloader(VendorDownloader):
    """ Eastward Energy-specific invoice downloader"""

    # Account metadata for filename generation
    ACCOUNT_METADATA = {
        0: {'vendor_number': 'HERI01', 'account_number': '4511', 'gl_account': '68100-YHZ-18-410'}
    }

    # Vendor metadata for pdfparsing
    VENDOR_METADATA = {
        'data_bbox': (0, 0, 0, 0), # Fill this in with specifics
        'date_format': '%b %d, %Y' # Change this with actual data values on invoice
    }

    def __init__(self):
        super().__init__(vendor_name='eastward', max_accounts=1) # Could change this to add more accounts later on

        # Load environment varialbes

        self.login_url = os.getenv('EASTWARD_LOGIN_URL')
        self.username = os.getenv('EASTWARD_USERNAME')
        self.password = os.getenv('EASTWARD_PASSWORD')

        # Validate
        if not all ([self.login_url, self.username, self.password]):
            raise ValueError("Eastward Variables must be set in .env")
        
    
    def login(self, account_index):
        """
        Eastward-specific login flow
        Note: account_index it not used for login, only for selecting which account
        """

        # Navigate to website
        self.logger.info(f"Navigating to {self.login_url}")
        self.page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)

        # Random human-like delay
        self.page.wait_for_timeout(random.randint(1000,3000))
        self.take_screenshot('01_login_page')


        try:
            # Page loads with focus on User ID field already
            # Enter username directly
            self.page.keyboard.type(self.username, delay = random.randint(100, 300))
            self.logger.debug(f"Username entered: {self.username}")
            self.page.wait_for_timeout(1000)

            # Fill password
            password_selector = '#Login_Password'
            self.page.wait_for_selector(password_selector, state='visible', timeout=10000)
            self.page.type(password_selector, self.password, delay= random.randint(100, 300))
            self.logger.debug("Password Entered!")
            self.page.wait_for_timeout(random.randint(500,1500))

            # Click Login Button
            self.page.click('#login')
            self.logger.info("Login button clicked")

            self.page.wait_for_timeout(120000)

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