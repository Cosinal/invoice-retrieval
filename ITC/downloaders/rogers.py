"""
Rogers Invoice Downloader
Implements Rogers-specific login and download logic

Last Modified: 12/10/2025
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
        

    # Helper Methods
    def _check_for_rc01_error(self):
        """ 
        Check if we're on the rc01 error page
        
        Returns:
            bool: True if rc01 error detected, False otherwise
        """

        try:
            # Check URL
            if 'error=rc01' in self.page.url:
                self.logger.warning("Detected rc01 error page in URL")
                return True
            
            # Check for error message text
            page_content = self.page.content()
            if 'rc01' in page_content.lower() or 'something went wrong' in page_content.lower():
                self.logger.warning("Detected rc01 error content")
                return True
            
            return False

        except Exception as e:
            self.logger.error(f"Error checking for rc01 error: {e}")
            return False
        
    
    def _recover_from_rc01(self):
        """
        Activates Gradnma mode and acts like a confused human who's never interacted with a website before
         
          
        Returns:
            bool: True if recovery successful, False otherwise
        """

        self.logger.info("[GRANDMA MODE] - recovering from rc01...'")
        self.take_screenshot('rc01_error_detected')

        try:
            # Acts confused - pauses and "reads" the error
            self.logger.info("Reading error message...")
            self.page.wait_for_timeout(random.randint(2000, 4000))

            # Random mouse movements (like a confused human)
            self.logger.info("Moving mouse around like a confused human...")
            for _ in range(random.randint(3, 6)):
                x = random.randint(100, 1000)
                y = random.randint(100, 600)
                self.page.mouse.move(x, y)
                self.page.wait_for_timeout(random.randint(300, 800))

            # Scroll around (like readint the page)
            self.logger.info("Scrolling around the page...")
            for _ in range(random.randint(2, 4)):
                scroll_amount = random.randint(-200, 200)
                self.page.mouse.wheel(0, scroll_amount)
                self.page.wait_for_timeout(random.randint(500, 1200))

            # Random clicks in empty area 
            self.logger.info("Clicking randomly on the page...")
            safe_zones = [(300, 400), (500, 300), (700, 500)]
            for zone in random.sample(safe_zones, k=random.randint(1, 2)):
               x, y = zone
               x += random.randint(-50, 50)
               y += random.randint(-50, 50)
               self.page.mouse.click(x, y)
               self.page.wait_for_timeout(random.randint(400, 900))

            # Now find and slowly move to "Try Again" button
            self.logger.info("Looking for 'Try Again' button...")
            self.page.wait_for_timeout(random.randint(1500, 3000))

            # Find Try Again button (adjust selector based on actual Rogers page)
            try_again_selector = 'body > dam-root > div > div > div > dam-signin-callback > dam-app-tile > div > div > div > div > div > dam-shared-eas-error-page > div > div:nth-child(2) > button'

            try_again_button = self.page.locator(try_again_selector)

            # Get button position
            box = try_again_button.bounding_box()
            if not box:
                self.logger.error("Could not get button position")
                return False
            
            # Slowly move mouse toward button (slowly, in stages)
            self.logger.info("Moving mouse to 'Try Again' button...")
            current_x = random.randint(200, 400)
            current_y = random.randint(200, 400)

            target_x = box['x'] + box['width'] / 2
            target_y = box['y'] + box['height'] / 2

            # Move in 3-5 steps toward button
            steps = random.randint(3, 5)
            for i in range(steps):
                progress = (i + 1) / steps
                next_x = current_x + (target_x - current_x) * progress
                next_y = current_y + (target_y - current_y) * progress

                # Add some wobble 
                next_x += random.randint(-10, 10)
                next_y += random.randint(-10, 10)

                self.page.mouse.move(next_x, next_y)
                self.page.wait_for_timeout(random.randint(300, 700))

            # Final precise move to button center
            self.page.mouse.move(target_x, target_y)
            self.page.wait_for_timeout(random.randint(500, 1000))

            # Click Try Again
            self.logger.info("Clicking 'Try Again' button...")
            try_again_button.click()
            self.page.wait_for_timeout(random.randint(2000, 3500))

            self.take_screenshot('recovery_clicked_try_again')
            self.logger.info("[GRANDMA MODE] complete - returning to login")

            return True
    
        except Exception as e:
            self.logger.error(f" Recovery failed: {e}")
            self.take_screenshot('error_recovery_failed')
            return False
        
    def login(self, account_index):
        """
        Rogers-specific login flow
        Note: account_index is not used for login, only for selecting which account after login
        """

        self.logger.info("Performing login...")
        self.logger.info(f"Username: {self.username}")
        self.logger.info(f"Navigating to: {self.login_url}")

        self.page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)

        # Random human-like delay
        self.page.wait_for_timeout(random.randint(1000, 3000))
        self.take_screenshot('01_login_page')

        # Track retry attempts
        max_login_attempts = 2

        for attempt in range(max_login_attempts):
            try:
                if attempt > 0:
                    self.logger.info(f"[RETRY] Login attempt {attempt + 1} of {max_login_attempts}")
    
                # Fill username
                self.page.wait_for_selector('#ds-form-input-id-0', state ='visible', timeout=10000) # Until either selector loads or 10s passes
                self.page.fill('#ds-form-input-id-0', '') # Clear field
                self.page.type('#ds-form-input-id-0', self.username, delay=100) # Human-like typing
                self.logger.debug("Username entered")
                self.page.wait_for_timeout(1000)

                # Click continue
                self.page.click('body > app-root > div > div > div > div > div > div > div > div > ng-component > form > div.text-center.signInButton > button')
                self.page.wait_for_timeout(3000)

                # Check for rc01 error (happens after Continue, before password)
                if self._check_for_rc01_error():
                    if attempt < max_login_attempts - 1:
                        # We have tries left - recover and retry
                        self.logger.warning(f"rc01 error detected after clicking continue")

                        if self._recover_from_rc01():
                            # Recovery successful - "Try Again" button navigates back to login page
                            # Just continue to next attempt
                            self.logger.info("Recovered from rc01, waiting before retry login...")
                            self.page.wait_for_timeout(random.randint(25000, 50000)) # Wait 10-45s before retrying
                            continue
                        else:
                            # Recovery failed
                            raise Exception("Failed to recover from rc01 error")
                    else:
                        # Last attempt also failed
                        self.logger.error("Maximum login attempts reached - rc01 error persists")
                        self.take_screenshot('error_max_login_attempts_rc01')
                        raise Exception("Maximum login attempts reached - Stopping to avoid ban")

                # Fill password
                self.page.wait_for_selector('#input_password', timeout=10000) # Until either selector loads or 10s passes
                self.page.type('#input_password', self.password, delay=100) # Human-like typing
                self.logger.debug("Password entered")

                # Click login
                self.page.click('#LoginForm > div.text-center.signInButton > button > span')
                self.logger.info("Login button clicked")

                # Wait for account selector modal (specific element on post-login page)
                self.page.wait_for_selector(
                    '#ds-modal-container-0 > rss-account-selector',
                    state='visible',
                    timeout=20000
                )

                self.take_screenshot('02_after_login')
                self.logger.info("Login successful!")
                return # Success - exit the loop
            
            except PlaywrightTimeout as e:
                if attempt < max_login_attempts - 1:
                    self.logger.warning(f" Login timeout on attempt {attempt + 1}: {e} - retrying...")
                    continue
                else:
                    self.logger.error(f"Login timeout: {e}")
                    self.take_screenshot('error_login_timeout')
                    raise

            except Exception as e:
                if attempt < max_login_attempts - 1:
                    self.logger.warning(f" Login error on attempt {attempt + 1}: {e}")
                    continue
                else:
                    self.logger.error(f"Login failed: {e}", exc_info=True)
                    self.take_screenshot('error_login_failed')
                    raise

        # If we reach here, all attempts failed
        raise Exception("All login attempts failed")
                

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


       
    