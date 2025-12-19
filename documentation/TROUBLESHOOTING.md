# 🐛 Troubleshooting Guide

Common issues and solutions for the Invoice Automation System.

---

## Quick Diagnostic Steps

When something breaks:

1. **Check logs:** `ITC/logs/[vendor]_[timestamp].log`
2. **Check screenshots:** `ITC/logs/[number]_[step]_[timestamp].png`
3. **Check credentials:** Verify `.env` file has correct values
4. **Test manually:** Login to vendor portal yourself to verify it works
5. **Check network:** Ensure you can reach vendor websites

---

## Table of Contents

- [Login Issues](#login-issues)
- [Navigation Issues](#navigation-issues)
- [Download Issues](#download-issues)
- [Date Extraction Issues](#date-extraction-issues)
- [Email Issues](#email-issues)
- [Browser Issues](#browser-issues)
- [Vendor-Specific Issues](#vendor-specific-issues)
- [Web Interface Issues](#web-interface-issues)

---

## Login Issues

### Timeout Waiting for Login Element

**Symptom:**
```
TimeoutError: Waiting for selector '#username' failed: Timeout 10000ms exceeded
```

**Causes:**
- Vendor changed their login page layout
- Login URL is incorrect
- Page loads slower than expected
- Element selector is wrong

**Solutions:**

1. **Verify login URL is correct:**
```bash
   # Check .env file
   cat .env | grep LOGIN_URL
```

2. **Inspect vendor website:**
   - Open login page in browser
   - Press F12 (DevTools)
   - Right-click username field → Inspect
   - Note the actual selector (ID, class, name)

3. **Update selector in vendor file:**
```python
   # Old (broken)
   username_selector = '#username'
   
   # New (after inspection)
   username_selector = '#user-id-field'
```

4. **Increase timeout if page loads slowly:**
```python
   self.page.wait_for_selector(username_selector, state='visible', timeout=20000)
```

---

### Login Succeeds But Next Step Fails

**Symptom:**
- Login appears to work
- Next page never loads or wrong page appears

**Causes:**
- Credentials are incorrect
- Login button didn't actually submit
- Vendor requires additional verification step

**Solutions:**

1. **Verify credentials manually:**
   - Open vendor portal in browser
   - Try logging in with credentials from `.env`
   - Confirm login actually succeeds

2. **Check for error messages on page:**
```python
   # Add after login attempt
   error_selector = '.error-message'
   if self.page.is_visible(error_selector):
       error_text = self.page.inner_text(error_selector)
       self.logger.error(f"Login error: {error_text}")
```

3. **Check for additional verification:**
   - Some vendors add security questions after login
   - May need to implement additional step in login method

4. **Increase wait time after login:**
```python
   self.page.click(login_button)
   self.page.wait_for_timeout(5000)  # Wait 5 seconds
```

---

### Invalid Credentials Error

**Symptom:**
```
ValueError: [VENDOR] credentials must be set in .env file
```

**Causes:**
- Missing credentials in `.env` file
- Typo in environment variable name
- `.env` file doesn't exist

**Solutions:**

1. **Check `.env` file exists:**
```bash
   ls -la .env
```

2. **If missing, copy from template:**
```bash
   cp .env-example .env
```

3. **Verify variable names match:**
```bash
   # Check what's in .env
   cat .env | grep ROGERS
   
   # Should show:
   # ROGERS_LOGIN_URL=...
   # ROGERS_USERNAME=...
   # ROGERS_PASSWORD=...
```

4. **Check for typos:**
   - Variable names are case-sensitive
   - Must match exactly what's in vendor downloader code
   - No spaces around `=` sign

---

## Navigation Issues

### Can't Find Account Dropdown

**Symptom:**
```
TimeoutError: Waiting for selector 'select#account-selector' failed
```

**Causes:**
- Vendor changed dropdown element
- Using wrong selector
- Dropdown appears differently for different users
- Single-account user doesn't have dropdown

**Solutions:**

1. **Check if account actually has dropdown:**
   - Login to vendor portal manually
   - See if account selector exists
   - May be single-account (no dropdown needed)

2. **Inspect actual dropdown:**
   - Use browser DevTools to find correct selector
   - Dropdown might be custom component, not standard `<select>`

3. **Update selector:**
```python
   # If custom dropdown
   dropdown_selector = 'button.account-selector'
   self.page.click(dropdown_selector)
   
   # Then select option
   option_selector = f'li:has-text("{account_text}")'
   self.page.click(option_selector)
```

4. **Add single-account check:**
```python
   if self.max_accounts > 1:
       # Handle dropdown selection
   else:
       # Skip directly to billing page
```

---

### Selected Wrong Account

**Symptom:**
- Download succeeds but invoice is for wrong account
- Filename shows unexpected account number

**Causes:**
- Dropdown text doesn't match what's in code
- Account order changed on vendor portal
- Dropdown selected by index instead of text

**Solutions:**

1. **Verify dropdown text:**
   - Login manually and check exact dropdown text
   - May include extra spaces or formatting

2. **Update ACCOUNT_DISPLAY text:**
```python
   ACCOUNT_DISPLAY = {
       0: "270 GOUDEY DR",  # Must match exactly
       1: "438 CYGNET DR"
   }
```

3. **Use account number instead of text:**
```python
   # Select by value attribute
   account_value = self.ACCOUNT_METADATA[account_index]['account_number']
   self.page.select_option(dropdown_selector, value=account_value)
```

4. **Add verification after selection:**
```python
   # Confirm correct account is displayed
   displayed_account = self.page.inner_text('.current-account')
   expected_account = self.ACCOUNT_METADATA[account_index]['account_number']
   if expected_account not in displayed_account:
       raise ValueError(f"Wrong account selected: {displayed_account}")
```

---

### Can't Find Download Button

**Symptom:**
```
TimeoutError: Waiting for selector 'button:has-text("Download")' failed
```

**Causes:**
- Navigation didn't reach correct page
- Button text changed
- Button hidden behind modal or menu
- Invoice not available yet

**Solutions:**

1. **Check you're on correct page:**
```python
   # Log current URL
   self.logger.info(f"Current page: {self.page.url}")
   
   # Check for expected text on page
   if not self.page.is_visible('text=Invoice'):
       raise ValueError("Not on invoice page")
```

2. **Try alternative selectors:**
```python
   # Try multiple possible selectors
   selectors = [
       'button:has-text("Download")',
       'a:has-text("Download Invoice")',
       'button[aria-label="Download"]',
       '#download-invoice-btn'
   ]
   
   for selector in selectors:
       if self.page.is_visible(selector):
           self.page.click(selector)
           break
```

3. **Check for blocking modals:**
```python
   # Close any modals that might be in the way
   if self.page.is_visible('.modal-overlay'):
       self.page.click('.modal-close')
       self.page.wait_for_timeout(1000)
```

---

## Download Issues

### PDF Downloaded But Date Extraction Fails

**Symptom:**
```
WARNING - Could not extract invoice date, using current date
```

**Causes:**
- Vendor changed PDF format
- Date moved to different location on PDF
- Date format doesn't match pattern
- Bounding box coordinates are wrong

**Solutions:**

1. **Run bbox_finder on downloaded PDF:**
```bash
   python -m ITC.utils.bbox_finder ITC/invoices/temp_vendor_*.pdf
```

2. **Update date_bbox coordinates:**
```python
   VENDOR_METADATA = {
       'date_bbox': (130, 80, 210, 95),  # Update from bbox_finder
       'date_format': '%b %d, %Y'
   }
```

3. **Check date format matches:**
```python
   # If PDF shows "12-Nov-2025" but code expects "Nov 12, 2025"
   'date_format': '%d-%b-%Y'  # Update to match
```

4. **Add debug logging:**
```python
   # In download_invoice method, add:
   text = cropped.extract_text()
   self.logger.debug(f"Extracted text from bbox: '{text}'")
```

5. **Test extraction manually:**
```python
   import pdfplumber
   
   with pdfplumber.open('invoice.pdf') as pdf:
       page = pdf.pages[0]
       cropped = page.within_bbox((130, 80, 210, 95))
       print(cropped.extract_text())
```

---

### Download Button Clicked But No File Received

**Symptom:**
- Click appears to work
- No error thrown
- But no PDF file created

**Causes:**
- Download happens in new tab (not using expect_download)
- Download is AJAX/fetch call not browser download
- Download requires additional confirmation

**Solutions:**

1. **Check if PDF opens in new tab:**
```python
   # Use expect_page instead of expect_download
   with self.context.expect_page() as new_page_info:
       self.page.click(download_selector)
   
   pdf_page = new_page_info.value
   pdf_url = pdf_page.url
   
   # Fetch PDF content
   response = self.context.request.get(pdf_url)
   with open(temp_path, 'wb') as f:
       f.write(response.body())
```

2. **Check for confirmation modal:**
```python
   self.page.click(download_selector)
   
   # Wait for and click confirmation
   confirm_selector = 'button:has-text("Confirm")'
   if self.page.is_visible(confirm_selector, timeout=3000):
       self.page.click(confirm_selector)
   
   # Then expect download
   with self.page.expect_download() as download_info:
       # Download should start after confirmation
```

3. **Add longer wait for download:**
```python
   with self.page.expect_download(timeout=60000) as download_info:  # 60 seconds
       self.page.click(download_selector)
```

---

### Downloaded File is Not a PDF

**Symptom:**
- File downloaded successfully
- But file is HTML, JSON, or error page instead of PDF

**Causes:**
- Session expired or login failed silently
- Clicked wrong download link
- Vendor returns error as download

**Solutions:**

1. **Check file content before processing:**
```python
   # After download
   with open(temp_path, 'rb') as f:
       first_bytes = f.read(4)
   
   if first_bytes != b'%PDF':
       self.logger.error("Downloaded file is not a PDF")
       # Log file content for debugging
       with open(temp_path, 'r') as f:
           content = f.read(500)  # First 500 chars
           self.logger.error(f"File content: {content}")
       return None
```

2. **Verify you're still logged in:**
```python
   # Before download, check for logout indicators
   if self.page.is_visible('text=Sign In'):
       raise ValueError("Session expired - not logged in")
```

3. **Check response status:**
```python
   response = self.context.request.get(pdf_url)
   if response.status != 200:
       self.logger.error(f"HTTP {response.status}: {response.status_text}")
       return None
```

---

## Date Extraction Issues

### Date Contains Extra Text

**Symptom:**
```
Extracted text from bbox: 'Invoice Date: Nov 12, 2025'
Failed to parse with format '%b %d, %Y'
```

**Causes:**
- Bounding box too large, captures label text
- Date format doesn't account for extra text

**Solutions:**

1. **Tighten bounding box:**
   - Re-run `bbox_finder.py`
   - Use coordinates that capture only the date

2. **Strip label text:**
```python
   text = text.replace('Invoice Date:', '').strip()
```

3. **Update date format to include label:**
```python
   'date_format': 'Invoice Date: %b %d, %Y'
```

---

### Bilingual Dates (Manitoba Hydro-Style)

**Symptom:**
```
Extracted text: 'Nov NOV 12, 2025'
Date parsing failed
```

**Causes:**
- PDF contains duplicate month names in multiple languages

**Solutions:**

Override `extract_date_from_pdf` in vendor class:
```python
def extract_date_from_pdf(self, pdf_path, bbox_coords, date_format="%b %d, %Y"):
    """
    Manitoba Hydro specific: Strip duplicate French month name
    """
    import re
    import pdfplumber
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            cropped = first_page.within_bbox(bbox_coords)
            text = cropped.extract_text()
            
            if not text:
                return None
            
            text = text.strip()
            self.logger.debug(f"Extracted: '{text}'")
            
            # Remove duplicate month name (French)
            text = re.sub(r'\s[A-Z]{3}\s', ' ', text)
            self.logger.debug(f"After cleanup: '{text}'")
            
            # Parse cleaned text
            parsed_date = datetime.strptime(text, '%b %d %Y')
            return parsed_date
            
    except Exception as e:
        self.logger.error(f"Date extraction failed: {e}")
        return None
```

See `ITC/downloaders/mhydro.py` for full example.

---

## Email Issues

### Email Not Sending

**Symptom:**
```
Failed to send email: [Errno 111] Connection refused
```

**Causes:**
- SMTP credentials wrong
- SMTP server/port incorrect
- Network blocking SMTP port
- Gmail requires app password

**Solutions:**

1. **Test email configuration:**
```bash
   python -c "from ITC.integrations.email_notifier import EmailNotifier; EmailNotifier().test_connection()"
```

2. **Check SMTP settings in .env:**
```env
   EMAIL_SMTP_SERVER=smtp.gmail.com
   EMAIL_SMTP_PORT=587  # Use 587 for TLS, 465 for SSL
   EMAIL_USERNAME=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password  # NOT regular password
```

3. **For Gmail, use App Password:**
   - Go to Google Account → Security
   - Enable 2-Step Verification
   - Generate App Password
   - Use app password in `.env`

4. **Check firewall/network:**
```bash
   # Test SMTP connection
   telnet smtp.gmail.com 587
```

---

### Email Sent But No Attachments

**Symptom:**
- Email arrives
- But no PDF attachments included

**Causes:**
- Download failed but email still sent
- File path incorrect in email attachment code

**Solutions:**

1. **Check download actually succeeded:**
```python
   # In web_app.py run_automation_job
   if result:  # Only add to email list if download succeeded
       downloaded_files.append(result)
```

2. **Verify file exists before attaching:**
```python
   # In email_notifier.py
   invoice_path = Path(invoice_path)
   if not invoice_path.exists():
       self.logger.error(f"File not found: {invoice_path}")
       return False
```

---

### Email Shows Wrong Recipient

**Symptom:**
- Email sent to default recipient
- Not the override address specified in UI

**Causes:**
- Email override not being passed through
- Settings not saved correctly

**Solutions:**

1. **Check email override in UI:**
   - Enter email in override field
   - Check browser console for API errors

2. **Verify email passed to job:**
```python
   # In web_app.py, check job metadata
   job = job_manager.get_jobs(job_id)
   email_to = job.metadata.get('email_to')
   self.logger.info(f"Email override: {email_to}")
```

3. **Check email notifier receives it:**
```python
   # In email_notifier.py send_batch_invoices
   self.logger.info(f"Recipients: {recipients}")
```

---

## Browser Issues

### Browser Won't Launch

**Symptom:**
```
Error: Executable doesn't exist at /path/to/chromium
```

**Causes:**
- Playwright browsers not installed
- Edge browser not installed (for Rogers)

**Solutions:**

1. **Install Playwright browsers:**
```bash
   playwright install chromium
```

2. **For Rogers, install Edge:**
   - Windows: Download from microsoft.com/edge
   - Mac: Download from microsoft.com/edge
   - Linux: `sudo apt install microsoft-edge-stable`

3. **Verify installation:**
```bash
   playwright --version
```

---

### Rogers RC01 Error Loop

**Symptom:**
```
Detected rc01 error page in URL
[GRANDMA MODE] recovering from rc01...
```

**Causes:**
- Rogers bot detection triggered
- Using Chromium instead of Edge
- Too many rapid login attempts

**Solutions:**

1. **System auto-recovers:** Wait 30-50 seconds for automatic retry

2. **If persistent, check browser:**
```python
   # In base.py, verify Edge is being used
   self.browser = playwright.chromium.launch(
       channel="msedge"  # Must use Edge for Rogers
   )
```

3. **Verify Edge is installed:**
```bash
   # Check Edge installation
   which microsoft-edge
```

4. **If still failing after 2 attempts:**
   - Wait 5-10 minutes before trying again
   - Rogers may have temporarily blocked your IP

---

### Headless Mode Not Working

**Symptom:**
- Set `HEADLESS_MODE=true`
- But browser windows still appear

**Causes:**
- Base class not respecting headless parameter
- Edge doesn't support headless mode

**Solutions:**

1. **Check base.py:**
```python
   # Should use headless parameter, not hardcoded False
   self.browser = playwright.chromium.launch(
       headless=headless,  # Should use parameter
       channel="msedge"
   )
```

2. **Rogers requires visible browser:**
   - Edge doesn't support headless mode
   - Rogers downloads will always show browser window
   - This is expected behavior

3. **Other vendors can run headless:**
   - Manitoba Hydro and Halifax Water use Chromium
   - Can run in headless mode successfully

---

## Vendor-Specific Issues

### Rogers: Account Selector Not Appearing

**Symptom:**
- Login succeeds
- But account selector modal doesn't appear

**Causes:**
- Single-account login
- Vendor changed post-login page

**Solutions:**

1. **Check if account has multiple accounts:**
   - Login manually to Rogers portal
   - See if account selector appears
   - Single-account users skip directly to dashboard

2. **Update selector:**
```python
   # Wait for account selector OR dashboard
   account_selector = '#ds-modal-container-0 > rss-account-selector'
   dashboard = '.dashboard-content'
   
   if self.page.is_visible(account_selector):
       # Multi-account flow
   else:
       # Single-account flow
```

---

### Halifax Water: Dropdown Switch Modal

**Symptom:**
- Dropdown selection triggers confirmation modal
- Automation hangs waiting

**Solution:**

Handle confirmation modal in navigation:
```python
# After clicking dropdown option
try:
    self.page.wait_for_selector('button:has-text("Switch")', state='visible', timeout=5000)
    self.page.click('button:has-text("Switch")')
    self.logger.info("Confirmed account switch")
except PlaywrightTimeout:
    # No modal appeared, continue
    pass
```

---

### Manitoba Hydro: Bill Date Format

**Symptom:**
- Date extraction fails
- Date format includes duplicate month names

**Solution:**

See [Bilingual Dates section](#bilingual-dates-manitoba-hydro-style) above.

---

## Web Interface Issues

### Can't Access http://localhost:5000

**Symptom:**
```
curl: (7) Failed to connect to localhost port 5000: Connection refused
```

**Causes:**
- Flask server not running
- Port 5000 already in use
- Firewall blocking access

**Solutions:**

1. **Start Flask server:**
```bash
   python web_app.py
```

2. **Check if port is in use:**
```bash
   # Check what's using port 5000
   lsof -i :5000
   
   # Or on Windows
   netstat -ano | findstr :5000
```

3. **Use different port:**
```python
   # In web_app.py, change:
   app.run(debug=True, port=5001)
```

---

### Download Button Does Nothing

**Symptom:**
- Click "Download All" button
- Nothing happens, no progress shown

**Causes:**
- JavaScript error in browser
- Another job already running
- API endpoint not responding

**Solutions:**

1. **Check browser console:**
   - Press F12
   - Look for JavaScript errors in Console tab
   - Check Network tab for failed API calls

2. **Check for active job:**
```bash
   # Server logs should show:
   # "A job is already running"
```

3. **Restart Flask server:**
```bash
   # Kill existing server
   Ctrl+C
   
   # Start again
   python web_app.py
```

---

### Progress Bar Stuck

**Symptom:**
- Progress bar stops updating mid-download
- Page shows "X of Y completed" but doesn't progress

**Causes:**
- Vendor download timed out
- Background thread crashed
- Job completed but UI not updated

**Solutions:**

1. **Check server logs:**
```bash
   # Look for errors in terminal where Flask is running
```

2. **Check job status manually:**
```bash
   # In browser console
   fetch('/api/job-status/[job_id]').then(r => r.json()).then(console.log)
```

3. **Refresh page:**
   - Refresh browser
   - If job completed, results should appear

4. **Check vendor logs:**
```bash
   # Find latest log
   ls -lt ITC/logs/*.log | head -1
   
   # Check for errors
   tail -50 [logfile]
```

---

## Getting More Help

### Enable Debug Logging

Add more detailed logging to troubleshoot issues:
```python
# In vendor downloader, add debug logs
self.logger.debug(f"Current URL: {self.page.url}")
self.logger.debug(f"Page title: {self.page.title()}")
self.logger.debug(f"Visible text: {self.page.inner_text('body')[:200]}")
```

### Screenshot Everything

Take screenshots at every step:
```python
self.take_screenshot('01_step_name')
# ... do something ...
self.take_screenshot('02_next_step')
```

### Test in Non-Headless Mode

See what's happening:
```bash
# In .env
HEADLESS_MODE=false
```

### Check Playwright Documentation

For browser automation issues:
- https://playwright.dev/python/docs/intro

### Review Existing Vendor Code

Similar issues may be solved in:
- `ITC/downloaders/rogers.py` - Bot detection handling
- `ITC/downloaders/halifaxwater.py` - Dropdown navigation
- `ITC/downloaders/mhydro.py` - Custom date parsing

---

## Still Stuck?

1. Check logs: `ITC/logs/[vendor]_[timestamp].log`
2. Check screenshots: `ITC/logs/*.png`
3. Review vendor implementation: `ITC/downloaders/[vendor].py`
4. Test manually: Login to vendor portal yourself
5. Check documentation: `documentation/ARCHITECTURE.md`
6. Contact development team with:
   - Error message from logs
   - Screenshots showing issue
   - Steps to reproduce
   - What you've already tried