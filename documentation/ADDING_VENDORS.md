# ➕ Adding New Vendors

This guide walks through the complete process of adding a new vendor to the Invoice Automation System.

**Time estimate:** 1-2 hours for simple portals, 4-6 hours for complex portals with bot detection or multi-account navigation.

---

## Prerequisites

Before starting, gather the following information:

- [ ] Vendor portal login URL
- [ ] Username and password for vendor account
- [ ] Sample invoice PDF (download manually first)
- [ ] Account number(s) from invoices
- [ ] Vendor number code (from accounting - typically 6 characters)
- [ ] GL account codes (from accounting)
- [ ] Property addresses (if vendor uses address-based account selection)

---

## Step-by-Step Process

### Step 1: Create Vendor File

Create a new Python file in `ITC/downloaders/` named after the vendor in lowercase with no spaces.

**Example:** For "Bell Canada" create `bell.py`

**File structure:**
```python
"""
Bell Canada Invoice Downloader
Implements Bell-specific login and download logic

Last Modified: [Date]
"""

import os
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from .base import VendorDownloader

class BellDownloader(VendorDownloader):
    """Bell-specific invoice downloader"""
    
    # Will be filled in following steps
    pass
```

---

### Step 2: Define Account Metadata

Add account metadata dictionary. Each account needs:
- **vendor_number:** 6-character code (e.g., BELL01)
- **account_number:** Last 4 digits of vendor account number
- **gl_account:** GL account code from accounting

**Example:**
```python
ACCOUNT_METADATA = {
    0: {
        'vendor_number': 'BELL01',
        'account_number': '4521',
        'gl_account': '68050-YYC-11-410'
    },
    1: {
        'vendor_number': 'BELL01',
        'account_number': '8903',
        'gl_account': '68050-YYT-16-412'
    }
}
```

**Notes:**
- Keys are zero-indexed (0, 1, 2, etc.)
- vendor_number typically combines vendor abbreviation + sequence number
- account_number is usually last 4 digits from invoice
- GL codes come from accounting department

---

### Step 3: Define Vendor Metadata (Placeholder)

Add vendor metadata for PDF date extraction. Set coordinates to zeros initially - you'll fill these in Step 8.
```python
VENDOR_METADATA = {
    'date_bbox': (0, 0, 0, 0),  # Placeholder - update in Step 8
    'date_format': '%b %d, %Y'  # Adjust to match vendor's date format
}
```

**Common date formats:**
- `'%b %d, %Y'` → Nov 12, 2025
- `'%d %b %Y'` → 12 Nov 2025
- `'%B %d, %Y'` → November 12, 2025
- `'%m/%d/%Y'` → 11/12/2025

---

### Step 4: Initialize Class and Load Credentials

Implement `__init__` method to load credentials from environment variables.
```python
def __init__(self):
    super().__init__(vendor_name='bell', max_accounts=2)  # Adjust max_accounts
    
    # Load environment variables
    load_dotenv()
    
    # Load vendor-specific credentials
    self.login_url = os.getenv('BELL_LOGIN_URL')
    self.username = os.getenv('BELL_USERNAME')
    self.password = os.getenv('BELL_PASSWORD')
    
    # Validate credentials exist
    if not all([self.login_url, self.username, self.password]):
        raise ValueError("Bell credentials must be set in .env file")
```

**Add to `.env` file:**
```env
# Bell Canada
BELL_LOGIN_URL=https://bell.ca/login
BELL_USERNAME=user@company.com
BELL_PASSWORD=your_password
```

---

### Step 5: Implement Login Method

Navigate to vendor portal, enter credentials, and wait for successful authentication.

**Process:**
1. Open vendor website in browser manually
2. Use browser DevTools (F12) to inspect login form elements
3. Note CSS selectors for username field, password field, login button
4. Implement login method with appropriate waits

**Example:**
```python
def login(self, account_index):
    """
    Bell-specific login flow
    """
    self.logger.info(f"Navigating to {self.login_url}")
    self.page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)
    
    # Human-like delay
    self.page.wait_for_timeout(random.randint(1000, 3000))
    self.take_screenshot('01_login_page')
    
    try:
        # Wait for username field and enter credentials
        username_selector = '#username'  # Adjust based on inspection
        self.page.wait_for_selector(username_selector, state='visible', timeout=10000)
        self.page.type(username_selector, self.username, delay=random.randint(100, 300))
        self.logger.debug("Username entered")
        
        # Enter password
        password_selector = '#password'  # Adjust based on inspection
        self.page.type(password_selector, self.password, delay=random.randint(100, 300))
        self.logger.debug("Password entered")
        
        # Click login button
        login_button_selector = 'button[type="submit"]'  # Adjust based on inspection
        self.page.click(login_button_selector)
        self.logger.info("Login button clicked")
        
        # Wait for successful login (wait for element that appears after login)
        self.page.wait_for_selector('#account-dashboard', state='visible', timeout=20000)
        self.take_screenshot('02_after_login')
        self.logger.info("Login successful")
        
    except PlaywrightTimeout as e:
        self.logger.error(f"Login timeout: {e}")
        self.take_screenshot('error_login_timeout')
        raise
    except Exception as e:
        self.logger.error(f"Login failed: {e}", exc_info=True)
        self.take_screenshot('error_login_failed')
        raise
```

**Tips:**
- Use `random.randint()` for delays to appear more human
- Take screenshots at key steps for debugging
- Use specific selectors (IDs preferred over classes)
- Wait for elements to be visible before interacting
- Handle timeouts gracefully with error logging

---

### Step 6: Implement Navigation Method

Navigate from post-login page to the invoice download page for the specified account.

**For single-account vendors:**
```python
def navigate_to_invoices(self, account_index):
    """
    Navigate to invoices page (single account)
    """
    self.logger.info("Navigating to billing page")
    
    try:
        # Click billing/invoices menu item
        billing_selector = 'a[href*="billing"]'
        self.page.wait_for_selector(billing_selector, state='visible', timeout=15000)
        self.page.click(billing_selector)
        self.logger.info("Clicked billing menu")
        
        # Wait for invoice page to load
        invoice_selector = 'button:has-text("Download Invoice")'
        self.page.wait_for_selector(invoice_selector, state='visible', timeout=15000)
        self.take_screenshot('03_invoice_page')
        
    except Exception as e:
        self.logger.error(f"Navigation failed: {e}", exc_info=True)
        self.take_screenshot('error_navigation')
        raise
```

**For multi-account vendors (with dropdown):**
```python
def navigate_to_invoices(self, account_index):
    """
    Navigate to invoices page (multi-account with dropdown)
    """
    self.logger.info(f"Navigating to invoices for account #{account_index + 1}")
    
    try:
        # Open account dropdown
        dropdown_selector = 'select#account-selector'
        self.page.wait_for_selector(dropdown_selector, state='visible', timeout=15000)
        
        # Select account by value or text
        account_value = self.ACCOUNT_METADATA[account_index]['account_number']
        self.page.select_option(dropdown_selector, value=account_value)
        self.logger.info(f"Selected account {account_value}")
        
        # Wait for page to update
        self.page.wait_for_timeout(2000)
        
        # Navigate to billing
        billing_selector = 'a:has-text("View Bills")'
        self.page.click(billing_selector)
        
        # Wait for invoice page
        self.page.wait_for_selector('button:has-text("Download")', state='visible')
        self.take_screenshot(f'03_invoice_page_account_{account_index}')
        
    except Exception as e:
        self.logger.error(f"Navigation failed: {e}", exc_info=True)
        self.take_screenshot(f'error_navigation_account_{account_index}')
        raise
```

**Tips:**
- End on the page where download button is located
- For dropdowns, use exact text that appears in the dropdown
- Add waits after dropdown selection for page updates
- Screenshot shows which account was selected

---

### Step 7: Implement Download Method

Click download button, save PDF, extract date, generate filename, and return path.

**Two common patterns:**

**Pattern A: Browser Download**
```python
def download_invoice(self, account_index):
    """
    Download invoice (browser download)
    """
    self.logger.info(f"Downloading invoice for account #{account_index + 1}")
    
    try:
        # Click download button
        download_selector = 'button:has-text("Download Invoice")'
        self.page.wait_for_selector(download_selector, state='visible', timeout=15000)
        
        # Handle download
        with self.page.expect_download() as download_info:
            self.page.click(download_selector)
            self.logger.info("Clicked download button")
        
        download = download_info.value
        
        # Save to temporary file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        temp_filename = f"temp_bell_{account_index}_{timestamp}.pdf"
        temp_path = self.download_dir / temp_filename
        download.save_as(temp_path)
        self.logger.info(f"Downloaded to: {temp_filename}")
        
        # Extract invoice date from PDF
        invoice_date = self.extract_date_from_pdf(
            pdf_path=temp_path,
            bbox_coords=self.VENDOR_METADATA['date_bbox'],
            date_format=self.VENDOR_METADATA['date_format']
        )
        
        if invoice_date:
            self.logger.info(f"Extracted invoice date: {invoice_date.strftime('%Y-%m-%d')}")
        else:
            self.logger.warning("Could not extract date, using current date")
        
        # Generate standardized filename
        filename = self.generate_file_name(account_index, invoice_date)
        
        # Rename temp file to final filename
        final_path = self.download_dir / filename
        temp_path.rename(final_path)
        
        self.logger.info(f"Renamed to: {filename}")
        return str(final_path)
        
    except Exception as e:
        self.logger.error(f"Download failed: {e}", exc_info=True)
        self.take_screenshot(f'error_download_account_{account_index}')
        return None
```

**Pattern B: PDF Opens in New Tab**
```python
def download_invoice(self, account_index):
    """
    Download invoice (opens in new tab)
    """
    self.logger.info(f"Downloading invoice for account #{account_index + 1}")
    
    try:
        # Click view/download button (opens new tab)
        view_selector = 'a:has-text("View Invoice")'
        
        with self.context.expect_page() as new_page_info:
            self.page.click(view_selector)
            self.logger.info("Clicked view invoice")
        
        # Get the new page (PDF tab)
        pdf_page = new_page_info.value
        pdf_page.wait_for_load_state('load', timeout=30000)
        pdf_url = pdf_page.url
        self.logger.info(f"PDF loaded at: {pdf_url}")
        
        # Download PDF content
        response = self.context.request.get(pdf_url)
        
        if not response.ok:
            self.logger.error(f"Failed to download PDF: HTTP {response.status}")
            pdf_page.close()
            return None
        
        # Save to temporary file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        temp_filename = f"temp_bell_{account_index}_{timestamp}.pdf"
        temp_path = self.download_dir / temp_filename
        
        with open(temp_path, 'wb') as f:
            f.write(response.body())
        
        self.logger.info(f"Downloaded to: {temp_filename}")
        pdf_page.close()
        
        # Extract date and rename (same as Pattern A)
        invoice_date = self.extract_date_from_pdf(
            pdf_path=temp_path,
            bbox_coords=self.VENDOR_METADATA['date_bbox'],
            date_format=self.VENDOR_METADATA['date_format']
        )
        
        filename = self.generate_file_name(account_index, invoice_date)
        final_path = self.download_dir / filename
        temp_path.rename(final_path)
        
        self.logger.info(f"Renamed to: {filename}")
        return str(final_path)
        
    except Exception as e:
        self.logger.error(f"Download failed: {e}", exc_info=True)
        self.take_screenshot(f'error_download_account_{account_index}')
        return None
```

---

### Step 8: Find PDF Date Coordinates

Use the `bbox_finder.py` utility to locate the invoice date in the PDF.

**Process:**
1. Manually download a sample invoice from vendor portal
2. Run bbox finder tool:
```bash
   python -m ITC.utils.bbox_finder ITC/invoices/sample_invoice.pdf
```
3. Tool will display text locations and suggest coordinates
4. Copy suggested coordinates into `VENDOR_METADATA['date_bbox']`

**Example output:**
```
BBOX FINDER - Finding text coordinates in PDF
=====================================================

TEXT ELEMENTS (sorted top-to-bottom, left-to-right):
1. 'Invoice Date' 
   Position: x0=50.0, y0=80.0, x1=120.0, y1=95.0

2. 'Nov 12, 2025' Date?
   Position: x0=130.0, y0=80.0, x1=210.0, y1=95.0

SUGGESTED BOUNDING BOX:
Based on date text 'Nov 12, 2025':
  'date_bbox': (130, 80, 210, 95)
```

**Update your vendor metadata:**
```python
VENDOR_METADATA = {
    'date_bbox': (130, 80, 210, 95),  # From bbox_finder
    'date_format': '%b %d, %Y'
}
```

**If date format doesn't match:**
Adjust `date_format` to match what appears in the PDF. Run test download to verify.

---

### Step 9: Register Vendor in Web Application

Add vendor to `web_app.py` so it appears in the web interface.

**Open `web_app.py` and:**

1. **Import your vendor class:**
```python
   from ITC.downloaders.bell import BellDownloader
```

2. **Add to VENDORS dictionary:**
```python
   VENDORS = {
       'rogers': {
           'class': RogersDownloader,
           'accounts': 3
       },
       'mhydro': {
           'class': ManitobaHydroDownloader,
           'accounts': 1
       },
       'hwater': {
           'class': HalifaxWaterDownloader,
           'accounts': 2
       },
       'bell': {  # Add this
           'class': BellDownloader,
           'accounts': 2  # Match your ACCOUNT_METADATA count
       }
   }
```

---

### Step 10: Test

**Test via command line first:**
```bash
# Test account 0
python orchestrator.py bell 0

# Test account 1 (if multiple accounts)
python orchestrator.py bell 1
```

**Check for:**
- ✅ Login succeeds
- ✅ Navigation reaches correct page
- ✅ PDF downloads
- ✅ Date extracted correctly
- ✅ Filename formatted properly
- ✅ No errors in logs

**Then test via web interface:**
```bash
python web_app.py
```
- Open `http://localhost:5000`
- Verify Bell appears in vendor list
- Test individual account buttons
- Test "Download All" includes Bell accounts
- Verify email delivery works

**Review logs:**
```bash
# Check latest log
ls -lt ITC/logs/bell_*.log | head -1
```

---

## Common Issues and Solutions

### Issue: Timeout Waiting for Selector

**Symptom:** `TimeoutError: Waiting for selector '...' failed`

**Causes:**
- Selector is incorrect
- Element takes longer to load than expected
- Element is hidden or not visible

**Solutions:**
- Increase timeout: `timeout=30000` (30 seconds)
- Check selector is correct using browser DevTools
- Try alternative selectors (ID, class, aria-label, text content)
- Add wait before action: `self.page.wait_for_timeout(2000)`

---

### Issue: Date Extraction Fails

**Symptom:** Log shows "Could not extract date, using current date"

**Causes:**
- Coordinates don't match date location
- Date format string doesn't match PDF date

**Solutions:**
- Re-run `bbox_finder.py` on downloaded PDF
- Verify `date_format` matches exactly what's in PDF
- Check for extra spaces or special characters in extracted text
- Add debug logging to see what text is extracted:
```python
  text = cropped.extract_text()
  self.logger.debug(f"Extracted: '{text}'")
```

---

### Issue: Bot Detection / CAPTCHA

**Symptom:** Login fails with security challenge or CAPTCHA

**Causes:**
- Vendor detects automation
- Too many rapid requests
- User agent flagged

**Solutions:**
- Add random delays throughout flow
- Use Edge browser instead of Chromium
- Implement "grandma mode" (see `rogers.py` for example)
- Consider manual CAPTCHA solving or alternative authentication

---

### Issue: Two-Factor Authentication (2FA)

**Symptom:** Login requires code from email/SMS

**Current limitation:** System cannot handle 2FA automatically

**Options:**
1. Request vendor disable 2FA for automation account
2. Use vendor API if available (no portal login needed)
3. Implement manual intervention step
4. Mark vendor as partial implementation (see `enmax.py`, `eastward.py`)

---

## Vendor-Specific Considerations

### Rogers-Style Bot Detection
If vendor has aggressive bot detection:
- Use Edge browser (set in base.py)
- Implement retry logic with increasing delays
- Add mouse movement randomization
- See `rogers.py` RC01 recovery for example

### Halifax Water-Style Dropdowns
If vendor uses dropdowns with specific text:
- Store exact dropdown text in `ACCOUNT_METADATA`
- Use `.filter(has_text=target_text)` for selection
- Add confirmation modal handling if needed
- See `halifaxwater.py` for example

### Manitoba Hydro-Style Date Parsing
If vendor has unusual date formats:
- Override `extract_date_from_pdf()` method
- Add custom parsing logic
- See `mhydro.py` for bilingual date example

---

## Checklist

Before considering vendor complete:

- [ ] All three methods implemented (login, navigate, download)
- [ ] Credentials added to `.env`
- [ ] Account metadata defined for all accounts
- [ ] PDF date coordinates found and tested
- [ ] Vendor registered in `web_app.py`
- [ ] Command-line test successful for all accounts
- [ ] Web interface test successful
- [ ] Email delivery confirmed
- [ ] Logs reviewed for warnings/errors
- [ ] Screenshots captured at key steps
- [ ] Code follows existing vendor patterns
- [ ] Comments added for vendor-specific logic

---

## Next Steps

After successful vendor addition:
1. Update README.md supported vendors list
2. Document any vendor-specific quirks in code comments
3. Add vendor to batch download script (if used)
4. Train users on any vendor-specific considerations
5. Monitor first few production runs for issues

---

## Questions?

- Review existing vendor implementations: `rogers.py`, `mhydro.py`, `halifaxwater.py`
- Check logs in `ITC/logs/` for detailed execution traces
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- Consult [ARCHITECTURE.md](ARCHITECTURE.md) for system design details