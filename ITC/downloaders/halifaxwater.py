"""
Halifax Water Invoice Downloader
Implements Halifax Water - vendor specific logic

Last Modified: 12/17/2025
"""

import os
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from .base import VendorDownloader

class HalifaxWaterDownloader(VendorDownloader):
    """ Halifax Water - Vendor specific downloader """

    # Account Metadata for filename generation
    ACCOUNT_METADATA = {
        0: {'vendor_number': 'HALI01', 'account_number': '6893', 'gl_account': '68100-YHZ-11-412'}, # 270 Goudey
        1: {'vendor_number': 'HALI01', 'account_number': '1871', 'gl_account': '68000-YHZ-10-412'} # 438 Cygnet
    }

    # Account Display Metadata for navigation
    ACCOUNT_DISPLAY = {
        0: "270 GOUDEY DR",
        1: "438 CYGNET DR"
    }

    # Vendor metadata for pdfparsing
    VENDOR_METADATA = {
        'date_bbox': (529, 26, 596, 40), # Adjusted to invoices formatted on 12/17/2025
        'date_format': '%d %b %Y'
    }


    def __init__(self):
        super().__init__(vendor_name='hwater', max_accounts=2) 

        # Load environment variables
        load_dotenv()

        # Halifax Water - specific config
        self.login_url = os.getenv('HWATER_LOGIN_URL')
        self.username = os.getenv('HWATER_USERNAME')
        self.password = os.getenv('HWATER_PASSWORD')

        # Validate
        if not all ([self.login_url, self.username, self.password]):
            raise ValueError("Halifax Water variables need to be set in .env")
        
    def login(self, account_index):
        """
        Halifax Water - Login logic
        Note: There are only two accounts: index 0, and 1
        """

        # Navigate to website
        self.logger.info(f"Navigating to {self.login_url}")
        self.page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)

        # Random human-like delay
        self.page.wait_for_timeout(random.randint(1000, 3000))
        self.take_screenshot('01_login_page')

        try:
            # Selectors
            username_selector = 'input[placeholder="Username"]'
            password_selector = 'input[placeholder="Password"]'
            sign_in_selector = '#mxui_widget_DataView_2 > div > div > div.mx-name-container88 > button'

            # Navigate and Enter Username
            self.page.wait_for_selector(username_selector, state='visible', timeout=10000)
            self.page.type(username_selector, self.username, delay = random.randint(100, 300))
            self.logger.debug(f"Username entered: {self.username}")
            self.page.wait_for_timeout(1000)

            # Navigate and Enter Password
            self.page.wait_for_selector(password_selector, state='visible', timeout=10000)
            self.page.type(password_selector, self.password, delay = random.randint(100, 300))
            self.logger.debug("Password Entered!")
            self.page.wait_for_timeout(1000)

            # Click Login Button
            self.page.click(sign_in_selector)
            self.logger.info("Login Button Clicked!")

            # Waut for View Bill sector 
            view_bill_selector = 'a:has-text("Billing & Payments")'
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
        Halifax Water - specific navigation to invoices page
        1. Select Account from Dropdown
        2. Click 'Billing & Payments'
        3. Wait for "Bill" button to appear
        """
        
        self.logger.info(f"Navigating to the invoice for account #{account_index + 1}")

        try:
           # Step 1: Select Account from dropdown (If multiple accounts exist)
           if self.max_accounts > 1:
               target_text = self.ACCOUNT_DISPLAY[account_index]

               dropdown_selector = 'button.dropdown-toggle.dropdown-button'
               current_account_label_selector = 'p.mx-name-layout-snippetCall1-snippetCall2-text16'

               # Open dropdown
               self.page.wait_for_selector(dropdown_selector, state = 'visible', timeout = 10000)
               self.page.click(dropdown_selector)

               # Click desired account by text
               self.page.get_by_text(target_text, exact = False).click()
               self.logger.info(f"Clicked account option: {target_text}")

               # Confirm switch if modal appears
               switch_button_selector = 'button:has-text("Switch")'
               try:
                   self.page.wait_for_selector(switch_button_selector, state = 'visible', timeout = 5000)
                   self.page.click(switch_button_selector)

               except PlaywrightTimeout:
                   self.logger.info("No account switch confirmation needed")

                # Wait until the header shows the correct account
               header = self.page.locator(current_account_label_selector)
               header.wait_for(state = 'visible', timeout = 10000)
               header.filter(has_text=target_text).wait_for(timeout=30000)

               self.logger.info(f"Account successfully switched to: {target_text}")

           # Step 2: Click "Billing & Payments" menu
           self.logger.info("Navigating to Billing & Payments")

           billing_menu_selector = 'a:has-text("Billing & Payments")'
           self.page.wait_for_selector(billing_menu_selector, state='visible', timeout = 20000)
           self.page.click(billing_menu_selector)
           self.logger.info("Clicked 'Billing & Payments'")

           # Wait for billing page to load
           self.page.wait_for_timeout(3000)
           self.take_screenshot(f'04_billing_page_account_{account_index}')

        except Exception as e:
            self.logger.error(f"Navigation failed: {e}", exc_info=True)
            self.take_screenshot('error_navigation')
            raise


    def download_invoice(self, account_index):
        """
        Halifax Water - vendor specific downloading process
        PDF opens in new tab when clicking 'Bill'
        """
        
        self.logger.info("Downloading invoice...")

        try:
            bill_selector = 'button.billbtn'

            # Wait for at least one bill button to appear
            self.page.wait_for_selector(bill_selector, state='visible', timeout=20000)

            # Click the FIRST bill button (most recent invoice)
            # Use .first() to ensure we click the top one
            with self.context.expect_page() as new_page_info:
                self.page.locator(bill_selector).first.click()
                self.logger.info("Clicked first 'Bill' button")

            # Get the new page (PDF Tab)
            pdf_page = new_page_info.value

            # Wait for PDF to fully load
            pdf_page.wait_for_load_state('load', timeout=30000)
            pdf_url = pdf_page.url
            self.logger.info(f"PDF Loaded at: {pdf_url}")

            # Download the PDF content
            response = self.context.request.get(pdf_url)

            if not response.ok:
                self.logger.error(f"Failed to download PDF: HTTP {response.status}")
                pdf_page.close()
                return None

            # Save file temporarily
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_filename = f"temp_hwater_{account_index}_{timestamp}.pdf"
            temp_path = self.download_dir / temp_filename

            with open(temp_path, 'wb') as f:
                f.write(response.body())

            self.logger.info(f"Downloaded to temporary file: {temp_filename}")

            # Close the PDF tab
            pdf_page.close()

            # Extract invoice date from PDF using vendor-level metadata
            invoice_date = self.extract_date_from_pdf(
                pdf_path=temp_path,
                bbox_coords=self.VENDOR_METADATA['date_bbox'],
                date_format=self.VENDOR_METADATA['date_format']
            )

            if invoice_date:
                self.logger.info(f"Extracted invoice date: {invoice_date.strftime('%Y-%m-%d')}")
            else:
                self.logger.warning("Could not extract invoice date, using current date")
            
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
            try:

                self.take_screenshot(f'error_account_{account_index + 1}')
            except:
                self.logger.error("Could not take error screenshot (page closed)")
            return None
        
