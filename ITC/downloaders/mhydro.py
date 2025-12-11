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
        'date_bbox': (330, 99, 462, 111), # will adjust later
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
        Manitoba Hydro - specific navigation to invoices page
        """
        
        self.logger.info(f"Navigating to the invoice for account #{account_index + 1}")

        try:
            # The billing link should already be visible from login

            view_bill_selector = '#ContentPlaceHolder1_BillingUserControl_spn_ViewBill > div > a'
            self.page.wait_for_selector(
                view_bill_selector,
                state='visible',
                timeout=20000
            )

            self.logger.info("View Bill Link found!")
            self.take_screenshot('03_bill_link_ready')

        except Exception as e:
            self.logger.error(f"Navigation failed: {e}", exc_info=True)
            self.take_screenshot('error_navigation')
            raise


    def download_invoice(self, account_index):
        """
        Manitoba Hydro - specific download process
        PDF opens in new tab when clicking 'View Bill'
        """
        
        self.logger.info("Downloading invoice...")

        try:
            bill_selector = '#ContentPlaceHolder1_BillingUserControl_spn_ViewBill > div > a'

            # Click the View Bill link (Opens PDF if new tab and switches to it)
            with self.context.expect_page() as new_page_info:
                self.page.click(bill_selector)
                self.logger.info("Clicked 'View Bill'")

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
            temp_filename = f"temp_mhydro_{account_index}_{timestamp}.pdf"
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
            self.take_screenshot(f'error_account_{account_index + 1}')
            return None
        

    def extract_date_from_pdf(self, pdf_path, bbox_coords, date_format="%b %d, %Y"):
      """
      Manitoba Hydro specific: Strip duplicate French month name
      Overrides base class method
      """
      
      import re
      import pdfplumber

      try:
          with pdfplumber.open(pdf_path) as pdf:
              first_page = pdf.pages[0]
              cropped = first_page.within_bbox(bbox_coords)
              text = cropped.extract_text()

              if not text:
                  self.logger.warning("No text found in the bounding box. Use bbox_finder.py")
                  return None
              
              text = text.strip()
              self.logger.debug(f"Extracted text from bbox: '{text}")

              # Remove the duplicate French Month
              text = re.sub(r'\s[A-Z]{3}\s', ' ', text)
              self.logger.debug(f"After stripping French month: '{text}")

              # Parse
              parsed_date = datetime.strptime(text, '%b %d %Y')
              self.logger.info(f"Successfully parsed invoice date: {parsed_date.strftime('%Y-%m-%d')}")
              return parsed_date
          
      except Exception as e:
          self.logger.error(f"Failed to extract date from PDF: {e}", exc_info=True)
          return None