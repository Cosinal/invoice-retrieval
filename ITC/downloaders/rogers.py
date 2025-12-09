"""
Rogers Invoice Downloader
Implements Rogers-specific login and download logic

Last Modified: 12/2/2025
"""

import os
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from .base import VendorDownloader

class RogersDownloader(VendorDownloader):
    """ Rogers-specific invoice downloader"""

    # Account metadata for filename generation
    ACCOUNT_METADATA = {
        0: {'vendor_number': 'ROGE04', 'account_number': '3509', 'gl_account': '68050-YYT-11-410'},
        1: {'vendor_number': 'ROGE04', 'account_number': '7803', 'gl_account': '68050-YYT-16-412'},
        2: {'vendor_number': 'ROGE04', 'account_number': '8401', 'gl_account': '68050-YYT-10-410'}
    }

    # Vendor metadata for pdfparsing
    VENDOR_METADATA = {
        'date_bbox': (118.0, 44.0, 168.0, 54.0),
        'date_format': '%b %d, %Y'
    }

    def __init__(self):
        super().__init__(vendor_name='rogers', max_accounts=3) # Could pass a variable above class to easily change max_accounts or 'vendor_name'

        # Load environment variables
        load_dotenv()

        # Rogers-specific config
        self.login_url = os.getenv('ROGERS_LOGIN_URL')
        self.username = os.getenv('ROGERS_USERNAME')
        self.password = os.getenv('ROGERS_PASSWORD')

        # Validate 
        if not all ([self.login_url, self.username, self.password]):
            raise ValueError("ROGERS_LOGIN_URL, ROGERS_USERNAME, and ROGERS_PASSWORD must be set in the .env")
        
        
    def login(self, account_index):
        """
        Rogers-specific login flow
        Note: account_index is not used for login, only for selecting which account after login
        """

        self.logger.info("Performing login...")
        self.logger.info(f"Username: {self.username}")
        self.logger.info(f"Navigating to: {self.login_url}")

        self.page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)
        
        # Random human-like wait delay after page load
        self.page.wait_for_timeout(random.randint(1000, 3000))
        self.take_screenshot('01_login_page')

        try:
            # Wait for username field to be VISIBLE and READY
            username_selector = '#ds-form-input-id-0'
            self.page.wait_for_selector(username_selector, state='visible', timeout=15000)

            self.page.wait_for_timeout(500) # Extra wait to ensure page is stable (0.5s)

            # Clear any existing text and fill
            self.page.fill(username_selector, '')
            self.page.type(username_selector, self.username, delay=100) # Types the username with a delay between keystrokes

            # Verify the text was actually entered
            entered_value = self.page.input_value(username_selector)
            if entered_value != self.username:
                self.logger.warning("Username not entered correctly. Expected {self.username}, got {entered_value}")

                # Retry once
                self.page.wait_for_timeout(1000)
                self.page.type(username_selector, self.username, delay=100)

            self.logger.debug("Username entered successfully")
            self.page.wait_for_timeout(random.randint(1500,3500)) # Human-like wait before continuing




            # Move mouse to continue button and click
            continue_button = 'body > app-root > div > div > div > div > div > div > div > div > ng-component > form > div.text-center.signInButton > button'
            self.page.wait_for_selector(continue_button, state='visible', timeout=10000)

            # Get button position and move mouse there
            box = self.page.locator(continue_button).bounding_box()
            if box:
                # Move mouse to button
                self.page.mouse.move(
                    box['x'] + box['width']/2 + random.randint(-5,5),
                    box['y'] + box['height']/2 + random.randint(-5,5)
                )
                self.page.wait_for_timeout(random.randint(300,700))

            # Click
            self.page.click(continue_button)
            self.logger.debug("Clicked 'Continue' button")

            # Wait for longer after clicking (server processing time)
            self.page.wait_for_timeout(random.randint(2000,4000))


            # Wait for password field to be VISIBLE and READY
            password_selector = '#input_password'
            self.page.wait_for_selector(password_selector, state='visible', timeout=15000)

            # Extra wait to ensure page is stable
            self.page.wait_for_timeout(500)

            # Clear and fill password
            self.page.fill(password_selector, '')
            self.page.type(password_selector, self.password, delay=80) #  Types the password with a delay between keystrokes
            self.page.wait_for_timeout(1000)

            # Verify password was entered (just check it's non-empty)
            entered_password = self.page.input_value(password_selector)
            if not entered_password:
                self.logger.warning("Password not entered correctly, retrying")

                # Retry once
                self.page.wait_for_timeout(1000)
                self.page.fill(password_selector, self.password)

            self.logger.debug("Password entered successfully")

            # Click login
            login_button = '#LoginForm > div.text-center.signInButton > button > span'

            self.page.wait_for_selector(login_button, state='visible', timeout=10000)
            self.page.click(login_button)
            self.logger.info("Login button clicked")

            # Wait for post-login
            self.page.wait_for_selector('#ds-modal-container-0 > rss-account-selector', state='visible', timeout=30000) # 30s
            self.take_screenshot('02_after_login')
            self.logger.info("Login successful!")
        
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
        Rogers-specific navigation to invoices page
        This is where we SELECT which account (0, 1, or 2)
        """
        
        self.logger.info(f"Selecting account #{account_index + 1}...")

        try:
            # Click the account button for the specific account
            account_buttons = self.page.locator('#ds-modal-container-0 > rss-account-selector > ds-modal > div.ds-modal__wrapper.d-flex.flex-column.h-100.px-sm-40.px-24 > div.ds-modal__body.px-24.px-sm-40.pb-40 > div > div > a')
            account_buttons.nth(account_index).click()
            self.logger.info(f"Selected account #{account_index + 1}")

            # Wait for "View your Bill"
            view_bill_selector = 'a[aria-label*="View bill for account number"]'
            self.page.wait_for_selector(view_bill_selector, state='visible', timeout=15000 )
            self.logger.info(f"Account page loaded for account #{account_index + 1}")
            self.take_screenshot(f'03_account_{account_index + 1}')

            # Click "View your Bill"
            self.page.wait_for_timeout(2000) # Wait for 2s
            self.page.locator(view_bill_selector).scroll_into_view_if_needed()
            self.page.wait_for_timeout(1000)
            self.page.click(view_bill_selector, force=True)
            self.logger.info(f"Clicked 'View your Bill' for account #{account_index + 1}")

            # Wait for bill page
            save_pdf_selector = save_pdf_selector = "#mainContent > rss-view-bill > div > div.col-xs-12.ng-star-inserted > rss-brite-bill > rss-bill-control-panel > div.col-xs-12.col-md-8 > rss-save-bill > div > div.d-sm-flex.flex-sm-row.mt-8.justify-content-end.saveBillContent > button:nth-child(2)"
            self.page.wait_for_selector(save_pdf_selector, state='visible', timeout=15000)
            self.logger.info(f"Bill page loaded for account #{account_index + 1}")
            self.take_screenshot(f'04_bill_page_{account_index + 1}')

        except Exception as e:
            self.logger.error(f"Navigation failed: {e}", exc_info=True)
            self.take_screenshot(f'error_navigation_{account_index + 1}')
            raise

    def download_invoice(self, account_index):
        """ 
        Rogers-specific download process
        """

        self.logger.info(f"Downloading invoice for account #{account_index + 1}...")

        try:
            # Click "Save PDF"
            save_pdf_selector = "#mainContent > rss-view-bill > div > div.col-xs-12.ng-star-inserted > rss-brite-bill > rss-bill-control-panel > div.col-xs-12.col-md-8 > rss-save-bill > div > div.d-sm-flex.flex-sm-row.mt-8.justify-content-end.saveBillContent > button:nth-child(2)"
            self.page.wait_for_selector(save_pdf_selector, timeout=10000)

            self.page.locator(save_pdf_selector).scroll_into_view_if_needed()
            self.page.click(save_pdf_selector)
            self.logger.info("Clicked 'Save PDF'")

            # Wait for modal
            self.page.wait_for_timeout(2000) # 2s
            self.take_screenshot(f'05_save_modal_{account_index + 1}')

            # Click "Download bills"
            download_selector = "#ds-modal-container-1 > rss-save-pdf-modal > ds-modal > div.ds-modal__wrapper.d-flex.flex-column.h-100.px-sm-40.px-24.pt-24.ds-border-top > div.ds-modal__fixedContent.mt-24.pt-24.ds-border-top > div > div.ds-modal__footer.mb-24.mb-sm-40 > div > button.ds-button.ds-pointer.text-center.mw-100.d-inline-block.-primary.-large.text-no-decoration"
            self.page.wait_for_selector(download_selector, timeout=10000) # Wait for 10s?

            # Download file
            with self.page.expect_download() as download_info:
                self.page.click(download_selector)
                self.logger.info("Clicked 'Download bills'")

            # Save file temporarily
            download = download_info.value
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_filename = f"temp_rogers_{account_index}_{timestamp}.pdf"
            temp_path = self.download_dir / temp_filename
            download.save_as(temp_path)

            self.logger.info(f"Downloaded to temporary file: {temp_filename}")

            # Extract invoice date from PDF using vendor-level metadata
            invoice_date = self.extract_date_from_pdf(
                pdf_path=temp_path,
                bbox_coords=self.VENDOR_METADATA['date_bbox'],
                date_format=self.VENDOR_METADATA['date_format']
            )

            if invoice_date:
                self.logger.info(f"Extracted invoice date: {invoice_date.strftime('%Y-%m-%d')}")
            else:
                self.logger.warning("Could not extract invoice date from PDF, using current date")
            
            # Generate proper filename 
            filename = self.generate_file_name(account_index, invoice_date)

            # Rename temp file to final filename
            final_path = self.download_dir / filename
            temp_path.rename(final_path)

            self.logger.info(f"Successfully renamed to: {filename}")
            self.logger.info(f"Saved to: {final_path.absolute()}")
            
            return str(final_path)
        
        except Exception as e:
            self.logger.error(f"Failed to process account #{account_index + 1}: {e}")
            self.take_screenshot(f'error_account_{account_index + 1}')
            return None


       
    