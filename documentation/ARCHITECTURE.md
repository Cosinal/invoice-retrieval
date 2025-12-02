# 🏗️ System Architecture

## Overview

The ITC Invoice Downloader uses a **class-based inheritance pattern** to share common automation logic between vendors while allowing vendor-specific customization.

**Core Principle:** White the automation workflow once (login -> navigate -> download), let each vendor implement their specific details

---

## Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                      Orchestrator (CLI)                      │
│                  Handles user input & routing                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │     VendorDownloader (Base Class)         │
        │  - Common workflow (run method)           │
        │  - Shared utilities (logging, screenshots)│
        │  - Abstract methods (login, navigate, etc)│
        └───────────────────┬───────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Rogers     │    │     Bell     │    │    Telus     │
│ Downloader   │    │  Downloader  │    │  Downloader  │
│              │    │              │    │              │
│ Implements:  │    │ Implements:  │    │ Implements:  │
│ - login()    │    │ - login()    │    │ - login()    │
│ - navigate() │    │ - navigate() │    │ - navigate() │
│ - download() │    │ - download() │    │ - download() │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## Component Hierarchy

### 1. Orchestrator (`orchestrator.py`)

**Responsibility:** CLI entry point and vendor routing

**What it does:**
- Parse command-line arguments (`vendor`, `account_index`)
- Validates input (vendor exists, account in range)
- Instantiates the correct vendor downloader
- Calls the downloader's `run()` method
- Reports success/failure to user

**Key code:**
```python
VENDORS = {
    'rogers': RogersDownloader(),
    # Future vendors added here
}

downloader = VENDORS[vendor_name]
success = downloader.run(account_index, DOWNLOAD_PATH, headless=False)
```

### 2. Base Downloader (`ITC/downloaders/base.py`)

**Responsibility:** Shared automation logic and workflow orchestration

**Abstract Base Class Pattern:**
The base class defines the **workflow** but not the **implementation**. Each vendor must implement specific methods.

#### Common Workflow (Same for All Vendors)
```python
def run(self, account_index, download_path, headless=False):
    """Standard workflow - same for every vendor"""
    setup_download_directory()
    launch_browser()
    
    # These three methods are vendor-specific
    self.login(account_index)              # ← Vendor implements
    self.navigate_to_invoices(account_index)  # ← Vendor implements
    self.download_invoice(account_index)   # ← Vendor implements
    
    cleanup()
    return success
```
#### Shared Utilities (Available to All Vendors)

| Utility | Purpose |
|---------|---------|
| `_setup_logging()` | Creates vendor-specific log files |
| `setup_download_directory()` | Creates output folders |
| `take_screenshot()` | Captures page state for debugging |
| `wait_for_page_load()` | Waits for page network idle |
| `extract_date_from_pdf()` | Extracts invoice date from PDF |
| `generate_file_name()` | Creates standardized filenames |

#### Abstract Methods (Must Be Implemented)

Each vendor **must** implement these three methods:
```python
@abstractmethod
def login(self, account_index):
    """Navigate to vendor portal and authenticate"""
    pass

@abstractmethod
def navigate_to_invoices(self, account_index):
    """Select account and navigate to invoice page"""
    pass

@abstractmethod
def download_invoice(self, account_index):
    """Download PDF and return file path"""
    pass
```

---

### 3. Vendor Downloaders (`ITC/downloaders/{vendor}.py`)

**Responsibility:** Vendor-specific implementation details

#### Required Components

Each vendor downloader must define:

**1. Class Definition**
```python
class RogersDownloader(VendorDownloader):
    """Rogers-specific implementation"""
```

**2. Vendor Metadata** (shared across all accounts)
```python
VENDOR_METADATA = {
    'date_bbox': (130, 25, 210, 40),     # PDF coordinates for date
    'date_format': '%b %d, %Y'            # Date format in invoice
}
```

**3. Account Metadata** (unique per account)
```python
ACCOUNT_METADATA = {
    0: {
        'vendor_number': 'ROGE04',
        'account_number': '7803',
        'gl_account': '68050-YYT-11-410'
    },
    # Additional accounts...
}
```

**4. Three Implementation Methods**
```python
def login(self, account_index):
    # Rogers-specific selectors and login flow
    
def navigate_to_invoices(self, account_index):
    # Rogers-specific navigation and account selection
    
def download_invoice(self, account_index):
    # Rogers-specific download process
    # Extracts date, generates filename, returns path
```

---

## Data Flow

### Complete Download Flow
```
User Command
    ↓
python orchestrator.py rogers 0
    ↓
Orchestrator validates input
    ↓
Instantiates RogersDownloader
    ↓
Calls run(account_index=0, download_path="ITC/invoices")
    ↓
┌────────────────────────────────────┐
│    Base Class: run() method        │
├────────────────────────────────────┤
│ 1. Setup logging & directories     │
│ 2. Launch Playwright browser       │
│ 3. Call vendor.login(0)            │ ← Rogers implements
│ 4. Call vendor.navigate(0)         │ ← Rogers implements
│ 5. Call vendor.download(0)         │ ← Rogers implements
│ 6. Browser cleanup                 │
│ 7. Return success/failure          │
└────────────────────────────────────┘
    ↓
Rogers.download_invoice() flow:
    ├─ Click download button
    ├─ Save PDF to temp file
    ├─ Extract date from PDF (base class utility)
    ├─ Generate filename (base class utility)
    ├─ Rename temp → final filename
    └─ Return file path
    ↓
Base class logs success
    ↓
Orchestrator reports to user
```

---

## File Naming System

### Architecture

The file naming system uses a **two-level metadata approach**:

**Level 1: Vendor Metadata** (shared across all accounts)
- PDF date extraction coordinates
- Date format pattern

**Level 2: Account Metadata** (unique per account)
- Vendor number
- Account number
- GL account code

### Naming Formula
```
{vendor_number}_{account_number}_{date}_{gl_account}.pdf
```

**Generated by:**
```python
def generate_file_name(self, account_index, invoice_date=None):
    metadata = self.ACCOUNT_METADATA[account_index]
    date_obj = invoice_date or datetime.now()
    
    # Format: 12-Dec-2025
    date_str = date_obj.strftime("%#d-%b-%Y")  # Windows
    
    # Construct filename
    filename = f"{metadata['vendor_number']}_{metadata['account_number']}_{date_str}_{metadata['gl_account']}.pdf"
    
    return filename
```

**Example Output:**
```
ROGE04_7803_12-Dec-2025_68050-YYT-11-410.pdf
```

---

## PDF Date Extraction

### Why Extract Dates from PDFs?

Invoice filenames from vendors are inconsistent:
- `Rogers-2025-11-12.pdf` (Rogers)
- `bill_november.pdf` (hypothetical Bell)
- `invoice.pdf` (unhelpful)

**Solution:** Extract the actual invoice date from inside the PDF for consistent naming.

### Architecture

**Two-step process:**

**Step 1: Find the date location** (one-time setup per vendor)
```bash
python -m ITC.utils.bbox_finder sample_invoice.pdf
```

This identifies PDF coordinates (bounding box) where the date appears.

**Step 2: Extract date during download** (automatic)
```python
def download_invoice(self, account_index):
    # Download PDF to temp file
    temp_path = download_to_temp()
    
    # Extract date using vendor's bbox coordinates
    invoice_date = self.extract_date_from_pdf(
        pdf_path=temp_path,
        bbox_coords=self.VENDOR_METADATA['date_bbox'],
        date_format=self.VENDOR_METADATA['date_format']
    )
    
    # Generate standardized filename
    filename = self.generate_file_name(account_index, invoice_date)
    
    # Rename temp → final
    temp_path.rename(final_path)
```

### Bounding Box Concept

A **bounding box** is a rectangle defined by coordinates:
```
PDF Page (0,0 at top-left)
    ↓
    
    (x0,y0) ──────────┐
       │              │
       │  Nov 12, 2025│  ← Text we want to extract
       │              │
       └────────── (x1,y1)
```

**Coordinates:** `(x0, y0, x1, y1)` = `(130, 25, 210, 40)`

The `extract_date_from_pdf()` method:
1. Opens the PDF
2. Extracts text from this rectangle
3. Parses it using the date format (e.g., `%b %d, %Y`)
4. Returns a `datetime` object

---

## Browser Automation Strategy

### Playwright vs Selenium

**Choice:** Playwright

**Reasons:**
- Modern async architecture
- Better handling of SPAs (single-page applications)
- Built-in wait mechanisms
- Cross-browser support
- Active development

### Wait Strategy

**Problem:** Rogers website uses modern JavaScript - elements load dynamically.

**Solution:** Wait for **specific elements**, not page load.

**Bad approach (slow):**
```python
page.wait_for_load_state('networkidle', timeout=30000)  # Waits full 30 seconds
```

**Good approach (fast):**
```python
page.wait_for_selector('#specific-button', state='visible', timeout=15000)  # Waits 2-3 seconds
```

**Example in Rogers:**
```python
def navigate_to_invoices(self, account_index):
    # Click account
    account_buttons.nth(account_index).click()
    
    # Wait for specific element (not networkidle)
    self.page.wait_for_selector('a[aria-label*="View bill"]', state='visible')
    
    # Click view bill
    self.page.click('a[aria-label*="View bill"]')
    
    # Wait for save button (indicates bill loaded)
    self.page.wait_for_selector('#save-pdf-button', state='visible')
```

This reduces execution time from **90 seconds → 25 seconds**.

---

## Logging & Debugging

### Multi-Level Logging System

**Log File:** `ITC/logs/{vendor}_{timestamp}.log`

**Console Output:** Real-time progress

**Screenshots:** Automatic capture at key points

**Example log flow:**
```
2025-12-02 10:15:51 - Browser launched
2025-12-02 10:15:52 - Performing login...
2025-12-02 10:15:52 - Username entered
2025-12-02 10:15:53 - Login successful
2025-12-02 10:15:54 - Selected account #1
2025-12-02 10:15:55 - Bill page loaded
2025-12-02 10:15:57 - Downloaded: ROGE04_7803_12-Dec-2025_GL5100.pdf
```

**Screenshot naming:**
```
01_login_page_20251202_101551.png
02_after_login_20251202_101553.png
03_account_1_20251202_101554.png
04_bill_page_1_20251202_101555.png
05_save_modal_1_20251202_101556.png
error_login_timeout_20251202_101600.png  ← On failure
```

---

## Design Decisions & Tradeoffs

### 1. Class Inheritance vs Configuration Files

**Chosen:** Class inheritance

**Rationale:**
- Vendors have complex, multi-step workflows
- Each vendor's website is fundamentally different
- Code is more maintainable than giant config files
- Type safety and IDE support

**Tradeoff:** Requires Python knowledge vs pure configuration

---

### 2. Playwright Sync API vs Async

**Chosen:** Sync API (`sync_playwright`)

**Rationale:**
- Simpler code (no `async`/`await` complexity)
- Sequential workflow matches use case
- Not running multiple downloads in parallel

**Tradeoff:** Can't run multiple vendors simultaneously (not needed)

---

### 3. PDF Parsing vs Filename Regex

**Chosen:** PDF parsing with pdfplumber

**Rationale:**
- Vendor filenames are inconsistent
- Invoice date is authoritative source of truth
- Future-proof against vendor filename changes

**Tradeoff:** Additional dependency and parsing overhead

---

### 4. Environment Variables vs Config File

**Chosen:** `.env` file

**Rationale:**
- Standard practice for credentials
- Easy to exclude from version control
- Simple key-value format
- Supported by `python-dotenv`

**Tradeoff:** Less structure than YAML/JSON config

---

### 5. Headless Mode Default = False

**Chosen:** Visible browser by default

**Rationale:**
- Easier debugging during development
- Can watch automation in real-time
- Screenshots still capture errors

**Tradeoff:** Requires display (can't run on headless server without changing)

---

## Scalability Considerations

### Adding More Vendors

**Current:** 1 vendor (Rogers)  
**Target:** 10-15 vendors

**Scaling strategy:**
1. Each vendor is isolated in its own file
2. Orchestrator just maps vendor name → class
3. No code changes to base class or other vendors

**Adding Bell:**
```python
# 1. Create ITC/downloaders/bell.py
# 2. Implement BellDownloader(VendorDownloader)
# 3. Update orchestrator.py:
VENDORS = {
    'rogers': RogersDownloader(),
    'bell': BellDownloader(),  # ← One line
}
```

### Adding More Accounts per Vendor

**No code changes required** - just update metadata:
```python
ACCOUNT_METADATA = {
    0: {...},
    1: {...},
    2: {...},
    3: {...},  # ← Just add more
}

# Update max_accounts
super().__init__(vendor_name='rogers', max_accounts=4)
```

### Performance at Scale

**Current:** ~25 seconds per invoice  
**At scale (30 accounts):** ~12.5 minutes sequentially

**Future optimization options:**
- Parallel execution (async Playwright)
- Batch mode (download all accounts for one vendor in one session)
- Scheduled runs (cron/task scheduler)

---

## Extension Points

The architecture supports future enhancements without major refactoring:

### 1. Post-Download Actions

Add to base class `run()` method:
```python
downloaded_file = self.download_invoice(account_index)

# Extension point: post-processing
self.upload_to_sharepoint(downloaded_file)
self.send_email_notification(downloaded_file)
```

### 2. Vendor-Specific Validation

Override in vendor class:
```python
def validate_invoice(self, pdf_path):
    """Rogers-specific validation"""
    # Check for expected text, page count, etc.
```

### 3. Multi-Account Sessions

Optimize by reusing login session:
```python
def download_all_accounts(self):
    """Download all accounts in one browser session"""
    self.login(account_index=0)  # Login once
    
    for i in range(self.max_accounts):
        self.navigate_to_invoices(i)
        self.download_invoice(i)
```

---

## Security Architecture

### Credential Management

**Storage:** `.env` file (gitignored)  
**Access:** `python-dotenv` loads into environment variables  
**Scope:** Process-level only (not persistent)

**Never stored in:**
- Version control (git)
- Log files
- Screenshots
- Downloaded filenames

### Browser Security

**Headless mode considerations:**
- Non-headless: User can see credentials being entered
- Headless: Credentials not visible on screen
- Production: Use headless=True

**Network security:**
- Playwright uses system browser (Chrome/Chromium)
- Respects system proxy settings
- No credential transmission to third parties

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.13+ | Core implementation |
| Browser Automation | Playwright | Web scraping |
| PDF Processing | pdfplumber | Date extraction |
| Environment Config | python-dotenv | Credential management |
| Logging | Python logging | Debug & audit trail |

**Key Dependencies:**
```txt
playwright==1.48.0
pdfplumber==0.11.4
python-dotenv==1.0.1
```