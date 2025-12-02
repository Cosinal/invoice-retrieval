"""
Base Downloader Class
All vendor-specif downloaders inherit from this
"""

import logging

from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout



class VendorDownloader(ABC):
    """
    Base class for all vendor invoice downloaders

    Each vendor must implement:
    - login()
    - navigate_to_invoices()
    - download_invoice()
    """

    def __init__(self, vendor_name, max_accounts=3):
        self.vendor_name = vendor_name
        self.max_accounts = max_accounts
        self.logger = self._setup_logging()

        # Will be set during execution
        self.browser = None
        self.context = None
        self.page = None
        self.download_dir = None


    def _setup_logging(self):
        """ Setup logging for this vendor """
        log_dir = Path('ITC/logs')
        log_dir.mkdir(exist_ok=True, parents=True)

        log_filename = log_dir / f'{self.vendor_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )

        return logging.getLogger(self.vendor_name)
    

    def setup_download_directory(self, download_path):
        """ Create download directory if it doesn't exist """
        self.download_dir = Path(download_path)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Download directory: {self.download_dir.absolute()}")
        return self.download_dir
    
    def wait_for_page_load(self, timeout=30000):
        """ Wait for page to fully load """
        try:
            self.page.wait_for_load_state('networkidle', timeout=timeout)
            self.logger.debug("Page loaded successfully")
        except PlaywrightTimeout:
            self.logger.warning("Page load timeout - continuing anyway")

    def take_screenshot(self, name):
        """ Take a screenshot for debugging """
        log_dir = Path('ITC/Logs')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{name}_{timestamp}.png'
        self.page.screenshot(path=log_dir / filename)
        self.logger.debug(f"Screenshot saved: {filename}")


    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
    # ABSTRACT METHODS - Each vendor MUST implement these
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

    @abstractmethod
    def login(self, account_index):
        """
        Login to the vendor's portal
        Must be implemented by each vendor
        """
        pass

    @abstractmethod
    def navigate_to_invoices(self, account_index):
        """
        Navigate to the invoices page for a specific account
        Must be implemented by each vendor
        """
        pass

    @abstractmethod
    def download_invoice(self, account_index):
        """
        Download the invoice for a specific account
        Must be implemented by each vendor

        Returns:
            str: Path to downloaded file, or None if failed
        """
        pass

    
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
    # MAIN EXECUTION METHOD - Same for all vendors
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

    def run(self, account_index, download_path, headless=False):
        """
        Main execution method - same flow for all vendors
        
        Args:
            account_index: Which account to download (0, 1, 2, etc.)
            download_path: Where to save the invoices
            headless: Whether to run browser in headless mode
            
        Returns:
            bool: True if successful, False otherwise
        """

        self.setup_download_directory(download_path)

        self.logger.info("="*70)
        self.logger.info(f"=== {self.vendor_name.upper()} INVOICE DOWNLOADER ===")
        self.logger.info("="*70)
        self.logger.info(f"Target Account: #{account_index + 1}")
        self.logger.info("="*70)

        with sync_playwright() as playwright:
            try:
                
                # Launch browser
                self.browser = playwright.chromium.launch(
                    headless=headless,
                    slow_mo=500
                )
                self.logger.info("Browser launched")

                self.context = self.browser.new_context(
                    accept_downloads=True,
                    viewport={
                        'width': 1920,
                        'height': 1080
                    }
                )

                self.page = self.context.new_page()

                # Execute vendor-specific methods
                self.login(account_index)
                self.navigate_to_invoices(account_index)
                downloaded_file = self.download_invoice(account_index)

                # Cleanup
                self.logger.info("Closing browser...")
                self.context.close()
                self.browser.close()

                if downloaded_file:
                    self.logger.info(f"SUCCESS: {downloaded_file}")
                    return True
                else:
                    self.logger.error("FAILED: No file downloaded")
                    return False
            
            except Exception as e:
                self.logger.error(f"Critical Error: {e}", exc_info=True)
                if self.browser:
                    self.browser.close()
                return False