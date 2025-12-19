# 🏗️ System Architecture

## Overview

The Invoice Automation System uses a **class-based inheritance pattern** to share common automation logic between vendors while allowing vendor-specific customization. The system consists of a Flask web application frontend with background job processing for browser automation.

**Core Principle:** Write the automation workflow once (login → navigate → download), let each vendor implement their specific details.

---

## High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                   Web Interface (Flask)                      │
│              Browser dashboard with progress UI              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │         Job Manager (Thread-Safe)          │
        │    - Tracks job state and progress         │
        │    - Stores results in memory              │
        │    - Provides status updates               │
        └───────────────────┬───────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │     Background Thread (Automation)         │
        │    - Iterates through vendors/accounts     │
        │    - Instantiates downloaders              │
        │    - Collects results                      │
        └───────────────────┬───────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Rogers     │    │Manitoba Hydro│    │Halifax Water │
│ Downloader   │    │  Downloader  │    │  Downloader  │
│              │    │              │    │              │
│ Implements:  │    │ Implements:  │    │ Implements:  │
│ - login()    │    │ - login()    │    │ - login()    │
│ - navigate() │    │ - navigate() │    │ - navigate() │
│ - download() │    │ - download() │    │ - download() │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                ┌───────────────────────┐
                │   Email Notifier      │
                │ - Batch email sender  │
                │ - Failure reporting   │
                └───────────────────────┘
```

---

## Component Hierarchy

### 1. Web Application (`web_app.py`)

**Responsibility:** HTTP server and user interface

**What it does:**
- Serves static HTML dashboard at `http://localhost:5000`
- Provides REST API endpoints for job management
- Spawns background threads for download jobs
- Manages user settings (email preferences)
- Coordinates job manager and email notifier

**Key endpoints:**
```python
@app.route('/')                    # Serve dashboard
@app.route('/api/start-job')       # Start download job
@app.route('/api/job-status/<id>') # Get job progress
@app.route('/api/vendors')         # List configured vendors
@app.route('/api/user/settings')   # Get/update user settings
```

**Vendor configuration:**
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
    }
}
```

---

### 2. Job Manager (`ITC/web/job_manager.py`)

**Responsibility:** Thread-safe job state tracking

**What it does:**
- Creates unique job IDs
- Stores job metadata (mode, email override)
- Tracks progress (completed/total accounts)
- Updates current vendor/account being processed
- Stores results (success/failure per account)
- Provides thread-safe access to job state

**Job lifecycle:**
```python
# Create job
job_id = job_manager.create_job(mode='all', metadata={'email_to': 'user@example.com'})

# Update progress
job_manager.update_progress(job_id, completed=1, total=6)
job_manager.update_current_task(job_id, vendor='rogers', account=0)

# Add results
job_manager.add_result(job_id, {
    'vendor': 'rogers',
    'account': 0,
    'success': True,
    'filename': 'ROGE04_7803_15-Dec-2025_68050-YYT-16-412.pdf'
})

# Mark complete
job_manager.mark_complete(job_id)
```

**Thread safety:**
- Uses `threading.Lock()` for all state modifications
- Safe concurrent access from Flask server and background threads

---

### 3. Background Thread (`run_automation_job`)

**Responsibility:** Execute download workflow in background

**What it does:**
- Runs in separate thread spawned by Flask
- Iterates through vendors and accounts
- Instantiates appropriate downloader for each
- Calls `run()` method on each downloader
- Updates job manager with progress
- Collects downloaded files
- Sends batch email at completion

**Execution flow:**
```python
def run_automation_job(job_id, mode, vendor_name, account_index, email_override):
    # Determine what to download
    if mode == 'all':
        jobs = [(v, a) for v in VENDORS for a in range(VENDORS[v]['accounts'])]
    else:
        jobs = [(vendor_name, account_index)]
    
    # Process each job
    for vendor, account in jobs:
        downloader = VENDORS[vendor]['class']()
        result = downloader.run(account, DOWNLOAD_PATH, headless=True)
        
        if result:
            downloaded_files.append(result)
            job_manager.add_result(job_id, success_result)
        else:
            job_manager.add_result(job_id, failure_result)
    
    # Send batch email
    email_notifier.send_batch_invoices(downloaded_files, failures, email_to)
    
    # Mark complete
    job_manager.mark_complete(job_id)
```

---

### 4. Base Downloader (`ITC/downloaders/base.py`)

**Responsibility:** Shared automation logic and workflow orchestration

**Abstract Base Class Pattern:**
The base class defines the **workflow** but not the **implementation**. Each vendor must implement specific methods.

#### Common Workflow (Same for All Vendors)
```python
def run(self, account_index, download_path, headless=False):
    """Standard workflow - same for every vendor"""
    try:
        # Setup
        self._setup_logging()
        self.setup_download_directory(download_path)
        
        # Launch browser
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        
        # Three vendor-specific steps
        self.login(account_index)              # ← Vendor implements
        self.navigate_to_invoices(account_index)  # ← Vendor implements
        file_path = self.download_invoice(account_index)  # ← Vendor implements
        
        # Cleanup
        self.browser.close()
        playwright.stop()
        
        return file_path
        
    except Exception as e:
        self.logger.error(f"Download failed: {e}", exc_info=True)
        self.take_screenshot(f'error_{account_index}')
        return None
```

#### Shared Utilities (Available to All Vendors)

| Utility | Purpose | Example Usage |
|---------|---------|---------------|
| `_setup_logging()` | Creates vendor-specific log files | Called in `run()` setup |
| `setup_download_directory()` | Creates `ITC/invoices/` folder | Called in `run()` setup |
| `take_screenshot(name)` | Captures page state for debugging | `self.take_screenshot('after_login')` |
| `extract_date_from_pdf()` | Extracts invoice date from PDF | Used in `download_invoice()` |
| `generate_file_name()` | Creates standardized filenames | Used after date extraction |

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

### 5. Vendor Downloaders (`ITC/downloaders/{vendor}.py`)

**Responsibility:** Vendor-specific implementation details

#### Required Components

Each vendor downloader must define:

**1. Class Definition**
```python
class RogersDownloader(VendorDownloader):
    """Rogers-specific implementation with RC01 recovery"""
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
    1: {
        'vendor_number': 'ROGE04',
        'account_number': '4156',
        'gl_account': '68050-YYC-11-410'
    }
    # Additional accounts...
}
```

**4. Credentials Loading**
```python
def __init__(self):
    super().__init__(vendor_name='rogers', max_accounts=3)
    
    load_dotenv()
    self.login_url = os.getenv('ROGERS_LOGIN_URL')
    self.username = os.getenv('ROGERS_USERNAME')
    self.password = os.getenv('ROGERS_PASSWORD')
    
    if not all([self.login_url, self.username, self.password]):
        raise ValueError("Rogers credentials must be set in .env file")
```

**5. Three Implementation Methods**
```python
def login(self, account_index):
    # Rogers-specific selectors and login flow
    # Handle RC01 bot detection if needed
    
def navigate_to_invoices(self, account_index):
    # Rogers-specific navigation and account selection
    # Handle account selector modal
    
def download_invoice(self, account_index):
    # Rogers-specific download process
    # Extract date, generate filename, return path
```

---

### 6. Email Notifier (`ITC/integrations/email_notifier.py`)

**Responsibility:** SMTP email delivery with attachments

**What it does:**
- Sends batch emails with multiple invoice attachments
- Generates failure reports for unsuccessful downloads
- Supports email override for one-time recipients
- Includes connection testing utility

**Batch email structure:**
```python
def send_batch_invoices(self, invoice_paths, failures, recipients):
    """
    Send single email with multiple PDF attachments
    
    Args:
        invoice_paths: List of paths to downloaded PDFs
        failures: List of failure dictionaries
        recipients: Email address(es) to send to
    """
    # Create message with all PDFs attached
    # Include failure report if any downloads failed
    # Send via SMTP
```

**Configuration (from .env):**
```env
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=default_recipient@company.com
```

---

### 7. Web Dashboard (`static/index.html`)

**Responsibility:** User interface for triggering downloads

**What it does:**
- Displays vendor list with individual account buttons
- Provides "Download All Invoices" button
- Shows real-time progress updates via polling
- Displays results with success/failure indicators
- Allows email override for one-time changes
- Saves user preferences (default email)

**Progress tracking:**
```javascript
// Poll job status every 2 seconds
setInterval(async () => {
    const status = await fetch(`/api/job-status/${jobId}`);
    const data = await status.json();
    
    // Update progress bar
    updateProgressBar(data.completed, data.total);
    
    // Show current task
    showCurrentTask(data.current_vendor, data.current_account);
    
    // Display results
    data.results.forEach(result => displayResult(result));
}, 2000);
```

---

## Data Flow

### Complete Download Flow (Web Interface)
```
User clicks "Download All"
    ↓
JavaScript sends POST to /api/start-job
    ↓
Flask creates job in job manager
    ↓
Flask spawns background thread
    ↓
Returns job_id to browser
    ↓
Browser starts polling /api/job-status/{job_id}
    ↓
┌────────────────────────────────────────────────────────┐
│           Background Thread Execution                  │
├────────────────────────────────────────────────────────┤
│ FOR EACH vendor/account:                               │
│   1. Instantiate vendor downloader                     │
│   2. Update job_manager.current_task                   │
│   3. Call downloader.run(account_index)                │
│      ├─ Base class: launch browser                     │
│      ├─ Vendor: login(account_index)                   │
│      ├─ Vendor: navigate_to_invoices(account_index)    │
│      ├─ Vendor: download_invoice(account_index)        │
│      │   ├─ Download PDF to temp file                  │
│      │   ├─ Extract date (base class utility)          │
│      │   ├─ Generate filename (base class utility)     │
│      │   └─ Rename temp → final                        │
│      └─ Base class: cleanup browser                    │
│   4. Update job_manager.progress                       │
│   5. Add result to job_manager                         │
│   6. Collect downloaded file path                      │
│                                                         │
│ AFTER ALL ACCOUNTS:                                    │
│   1. Call email_notifier.send_batch_invoices()         │
│   2. Mark job as complete                              │
└────────────────────────────────────────────────────────┘
    ↓
Browser receives "completed" status
    ↓
Displays final results and stops polling
    ↓
User receives email with all invoices
```

---

## File Naming System

### Architecture

The file naming system uses a **two-level metadata approach**:

**Level 1: Vendor Metadata** (shared across all accounts)
- PDF date extraction coordinates (`date_bbox`)
- Date format pattern (`date_format`)

**Level 2: Account Metadata** (unique per account)
- Vendor number (e.g., `ROGE04`)
- Account number (last 4 digits)
- GL account code (accounting code)

### Naming Formula
```
{vendor_number}_{account_number}_{date}_{gl_account}.pdf
```

**Example:**
```
ROGE04_7803_15-Dec-2025_68050-YYT-16-412.pdf
│      │     │           └─ GL account code
│      │     └─ Invoice date (from PDF)
│      └─ Account number (last 4 digits)
└─ Vendor code (6 characters)
```

**Generated by:**
```python
def generate_file_name(self, account_index, invoice_date=None):
    metadata = self.ACCOUNT_METADATA[account_index]
    date_obj = invoice_date or datetime.now()
    
    # Format: 15-Dec-2025
    date_str = date_obj.strftime("%d-%b-%Y")
    
    # Construct filename
    filename = f"{metadata['vendor_number']}_{metadata['account_number']}_{date_str}_{metadata['gl_account']}.pdf"
    
    return filename
```

---

## PDF Date Extraction

### Why Extract Dates from PDFs?

Invoice filenames from vendors are inconsistent and unreliable:
- `Rogers-2025-11-12.pdf` (Rogers)
- `bill.pdf` (Halifax Water)
- `invoice.pdf` (generic)

**Solution:** Extract the actual invoice date printed inside the PDF for authoritative, consistent naming.

### Two-Step Process

**Step 1: Find Date Location** (one-time setup per vendor)

Use the bbox_finder utility:
```bash
python -m ITC.utils.bbox_finder ITC/invoices/sample_invoice.pdf
```

Output shows text locations:
```
TEXT ELEMENTS:
1. 'Invoice Date' Position: x0=50, y0=80, x1=120, y1=95
2. 'Nov 12, 2025' Position: x0=130, y0=80, x1=210, y1=95

SUGGESTED BOUNDING BOX:
  'date_bbox': (130, 80, 210, 95)
```

**Step 2: Extract Date During Download** (automatic)
```python
def download_invoice(self, account_index):
    # Download PDF to temp file
    temp_path = self.download_dir / f"temp_{account_index}.pdf"
    
    # Extract date using vendor's bbox coordinates
    invoice_date = self.extract_date_from_pdf(
        pdf_path=temp_path,
        bbox_coords=self.VENDOR_METADATA['date_bbox'],
        date_format=self.VENDOR_METADATA['date_format']
    )
    
    # Generate standardized filename
    filename = self.generate_file_name(account_index, invoice_date)
    
    # Rename temp → final
    final_path = self.download_dir / filename
    temp_path.rename(final_path)
    
    return str(final_path)
```

### Bounding Box Concept

A **bounding box** is a rectangle defined by four coordinates:
```
PDF Page (0,0 at top-left)
    ↓
    
    (x0,y0) ──────────┐
       │              │
       │  Nov 12, 2025│  ← Text we want to extract
       │              │
       └────────── (x1,y1)
```

**Coordinates:** `(x0, y0, x1, y1)` = `(130, 80, 210, 95)`

The `extract_date_from_pdf()` method:
1. Opens the PDF with `pdfplumber`
2. Extracts text from the specified rectangle
3. Parses the text using the date format (e.g., `%b %d, %Y`)
4. Returns a `datetime` object
5. Falls back to current date if parsing fails

---

## Browser Automation Strategy

### Playwright Choice

**Why Playwright over Selenium:**
- Modern async architecture
- Better handling of single-page applications (SPAs)
- Built-in wait mechanisms for dynamic content
- Cross-browser support (Chromium, Firefox, WebKit)
- Active development and better documentation

### Wait Strategy

**Problem:** Vendor websites use modern JavaScript - elements load dynamically after page load.

**Solution:** Wait for **specific elements to appear**, not just page load events.

**Bad approach (slow and unreliable):**
```python
page.goto(url)
page.wait_for_load_state('networkidle', timeout=30000)  # Often waits full 30s
```

**Good approach (fast and reliable):**
```python
page.goto(url)
page.wait_for_selector('#login-button', state='visible', timeout=15000)  # 2-3s typical
```

**Real example from Rogers:**
```python
def navigate_to_invoices(self, account_index):
    # Click account selector
    account_buttons = self.page.locator('#account-selector button')
    account_buttons.nth(account_index).click()
    
    # Wait for specific element (not networkidle)
    self.page.wait_for_selector('a[aria-label*="View bill"]', state='visible')
    
    # Click view bill
    self.page.click('a[aria-label*="View bill"]')
    
    # Wait for download button (indicates bill loaded)
    self.page.wait_for_selector('button:has-text("Save as PDF")', state='visible')
```

**Performance impact:** Reduced execution time from **90 seconds → 25 seconds** per download.

### Browser Selection Strategy

Different vendors require different browsers:

| Vendor | Browser | Headless | Reason |
|--------|---------|----------|--------|
| Rogers | Edge | No | Bot detection bypass |
| Manitoba Hydro | Chromium | Yes | Standard automation |
| Halifax Water | Chromium | Yes | Standard automation |

**Implementation:**
```python
# In base.py, allow vendor-specific browser
if self.vendor_name == 'rogers':
    self.browser = playwright.chromium.launch(
        headless=False,  # Edge doesn't support headless
        channel="msedge"
    )
else:
    self.browser = playwright.chromium.launch(
        headless=headless
    )
```

---

## Logging & Debugging

### Multi-Level Logging System

**Log files:** `ITC/logs/{vendor}_{timestamp}.log`

**Console output:** Real-time progress in Flask terminal

**Screenshots:** Automatic capture at key points and errors

**Example log flow:**
```
2025-12-19 10:15:51 - INFO - Browser launched
2025-12-19 10:15:52 - INFO - Performing login...
2025-12-19 10:15:52 - DEBUG - Username entered
2025-12-19 10:15:53 - INFO - Login successful
2025-12-19 10:15:54 - INFO - Selected account #1 (7803)
2025-12-19 10:15:55 - INFO - Bill page loaded
2025-12-19 10:15:56 - INFO - Extracted invoice date: 2025-12-15
2025-12-19 10:15:57 - INFO - Downloaded: ROGE04_7803_15-Dec-2025_68050-YYT-16-412.pdf
```

**Screenshot naming convention:**
```
01_login_page_20251219_101551.png
02_after_login_20251219_101553.png
03_account_1_20251219_101554.png
04_bill_page_1_20251219_101555.png
error_login_timeout_20251219_101600.png  ← On failure
```

**Log levels:**
- `DEBUG`: Detailed step-by-step actions
- `INFO`: High-level progress milestones
- `WARNING`: Non-fatal issues (date extraction fallback)
- `ERROR`: Fatal errors with stack traces

---

## Design Decisions & Rationale

### 1. Class Inheritance vs Configuration Files

**Chosen:** Class inheritance

**Rationale:**
- Vendors have complex, multi-step workflows that differ fundamentally
- Rogers requires custom RC01 bot detection recovery logic
- Halifax Water needs special dropdown handling
- Manitoba Hydro requires custom date parsing
- Configuration files would become a programming language themselves
- Python provides type safety, IDE support, and debugging tools

**Tradeoff:** Requires Python knowledge to add vendors vs editing config files

**Example complexity that rules out config:**
```python
# Rogers RC01 recovery - can't express this in YAML
if 'rc01' in self.page.url.lower():
    self.logger.warning("RC01 detected - entering grandma mode")
    self.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
    self.page.wait_for_timeout(random.randint(30000, 50000))
    self.page.goto(self.login_url)
```

---

### 2. Sequential vs Parallel Downloads

**Chosen:** Sequential processing

**Rationale:**
- Vendor portals block simultaneous logins from same account
- Parallel attempts increase bot detection triggers (especially Rogers)
- Sequential takes ~25s per account = 2.5 minutes for 6 accounts
- This is acceptable given it eliminates 4 hours of manual work monthly
- Simpler error handling and progress tracking
- More reliable than parallel with constant retries

**Tradeoff:** Could be faster with parallelization, but reliability is more important

**Performance at scale:**
- Current: 6 accounts in 2.5 minutes
- Future (30 accounts): 12.5 minutes sequentially
- Still acceptable for automation vs manual process

---

### 3. PDF Parsing vs Filename Regex

**Chosen:** PDF content parsing with pdfplumber

**Rationale:**
- Vendor filenames are completely unreliable:
  - Rogers: Sometimes `Rogers-2025-11.pdf`, sometimes `invoice.pdf`
  - Halifax Water: Always `bill.pdf` (no date information)
  - Manitoba Hydro: Varies by month
- Invoice date printed on PDF is authoritative source
- Future-proof against vendor filename changes
- Ensures consistent, accurate naming for accounting

**Tradeoff:** Additional dependency and ~500ms parsing overhead per invoice

**Example benefit:**
```python
# Vendor provides: "invoice.pdf"
# After extraction: "ROGE04_7803_15-Dec-2025_68050-YYT-16-412.pdf"
# Accounting can now sort and process automatically
```

---

### 4. Web Interface vs CLI Only

**Chosen:** Flask web interface as primary interface

**Rationale:**
- Non-technical users (AP staff) need simple interface
- Real-time progress tracking improves user experience
- One-click batch downloads vs running multiple CLI commands
- Email override easier via form than command-line argument
- Progress visibility reduces "is it working?" support requests

**Tradeoff:** Additional complexity vs CLI-only, but essential for end users

**CLI still available** for testing and debugging:
```bash
python orchestrator.py rogers 0  # Test single account
```

---

### 5. In-Memory Job State vs Database

**Chosen:** In-memory job state with threading.Lock

**Rationale:**
- Simple deployment (no database required)
- Job state is transient (only matters during execution)
- Low volume (2-5 users, twice weekly usage)
- No need for job history beyond current execution
- Reduces dependencies and complexity

**Tradeoff:** Jobs lost if server restarts, but this is acceptable given usage pattern

**When to switch to database:**
- If job history needed for auditing
- If multiple servers needed (horizontal scaling)
- If job queue needed (scheduled execution)

---

### 6. Batch Email vs Individual Emails

**Chosen:** Single batch email with all invoices

**Rationale:**
- Reduces email clutter (1 email vs 6+ emails)
- All invoices arrive together for batch processing
- Single failure report rather than multiple emails
- Simpler to track and archive
- Better user experience

**Tradeoff:** All-or-nothing delivery, but SMTP reliability is high

---

## Scalability Considerations

### Adding More Vendors

**Current:** 3 vendors (Rogers, Manitoba Hydro, Halifax Water)  
**Target:** 10-15 vendors

**Scaling strategy:**
1. Each vendor isolated in own file
2. No changes to base class or other vendors
3. Web app just needs one-line registration

**Adding new vendor (Bell):**
```python
# 1. Create ITC/downloaders/bell.py
class BellDownloader(VendorDownloader):
    # Implement login, navigate, download

# 2. Register in web_app.py
VENDORS = {
    'rogers': {'class': RogersDownloader, 'accounts': 3},
    'mhydro': {'class': ManitobaHydroDownloader, 'accounts': 1},
    'hwater': {'class': HalifaxWaterDownloader, 'accounts': 2},
    'bell': {'class': BellDownloader, 'accounts': 2}  # ← One line
}
```

---

### Adding More Accounts per Vendor

**No code changes required** - only configuration:
```python
# In vendor downloader, just add to metadata
ACCOUNT_METADATA = {
    0: {...},
    1: {...},
    2: {...},
    3: {...},  # ← New account
}

# Update max_accounts
super().__init__(vendor_name='rogers', max_accounts=4)

# Update web_app.py
VENDORS = {
    'rogers': {'class': RogersDownloader, 'accounts': 4}  # ← Increment
}
```

---

### Performance at Scale

**Current performance:**
- ~25 seconds per account
- 6 accounts = 2.5 minutes total
- 93% time savings vs manual (4 hours → 5 minutes)

**Projected at scale:**
- 30 accounts = 12.5 minutes sequentially
- Still 94% time savings vs manual (10 hours → 40 minutes)

**Future optimization options:**
1. **Parallel execution with limits**
   - Run 2-3 vendors in parallel
   - Sequential within each vendor to avoid account conflicts

2. **Session reuse**
   - Login once, download all accounts for that vendor
   - Reduces overhead from multiple browser launches

3. **Scheduled execution**
   - Run automatically twice weekly via cron
   - Email results when complete
   - Zero user interaction required

---

## Extension Points

The architecture supports future enhancements without major refactoring:

### 1. User Authentication

Currently no authentication - runs on internal network.

**To add:**
```python
# In web_app.py
from flask_login import LoginManager, login_required

@app.route('/api/start-job')
@login_required  # ← Add decorator
def start_job():
    # Existing code
```

### 2. Scheduled Execution

Currently manual trigger only.

**To add:**
```python
# Use APScheduler
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    func=run_scheduled_downloads,
    trigger='cron',
    day_of_week='mon,thu',  # Monday and Thursday
    hour=8,
    minute=0
)
scheduler.start()
```

### 3. Job History Database

Currently in-memory only.

**To add:**
```python
# Switch to SQLite or PostgreSQL
class JobHistory:
    def save_job(self, job_id, results):
        # Store in database
        
    def get_job_history(self, user_id, date_range):
        # Query historical jobs
```

### 4. Additional Notification Methods

Currently email only.

**To add:**
```python
# In web_app.py after job completes
notifiers = [
    EmailNotifier(),
    SlackNotifier(),    # Post to Slack channel
    TeamsNotifier(),    # Post to MS Teams
]

for notifier in notifiers:
    notifier.send(results)
```

### 5. Vendor-Specific Validation

Validate invoices before accepting them.

**To add in base class:**
```python
def validate_invoice(self, pdf_path):
    """Override in vendor class for custom validation"""
    return True

# In vendor class
def validate_invoice(self, pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()
        if 'PAST DUE' in text:
            self.logger.warning("Invoice is past due")
        if pdf.pages[0].chars.__len__() < 100:
            raise ValueError("PDF appears empty or corrupted")
    return True
```

---

## Security Architecture

### Credential Management

**Current storage:** `.env` file (gitignored, plain text)

**Access pattern:**
```python
load_dotenv()  # Load into environment variables
username = os.getenv('ROGERS_USERNAME')  # Access in code
```

**Never stored in:**
- Version control (`.gitignore` excludes `.env`)
- Log files (passwords never logged)
- Screenshots (captured after login)
- Downloaded filenames
- Email bodies
- Database (no database currently)

**Production deployment:**
- Transfer to IT credential vault
- Use system environment variables
- Or encrypted configuration management
- Code unchanged (still uses `os.getenv()`)

### Browser Security

**Headless mode:**
- Rogers: Visible browser (credentials briefly visible on screen)
- Others: Headless mode (no visible credentials)

**Network security:**
- Outbound connections only (to vendor portals and SMTP)
- No inbound connections except Flask HTTP port
- Respects system proxy settings
- No telemetry or external API calls

**Session isolation:**
- Each download gets new browser context
- Cookies cleared after each job
- No persistent browser data

---

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.13+ | Core implementation |
| Web Framework | Flask | 3.1.0 | HTTP server and API |
| Browser Automation | Playwright | 1.48.0 | Web scraping |
| PDF Processing | pdfplumber | 0.11.4 | Date extraction |
| Environment Config | python-dotenv | 1.0.1 | Credential management |
| Email | smtplib | stdlib | SMTP email delivery |
| Logging | logging | stdlib | Debug and audit trail |
| Threading | threading | stdlib | Background jobs |

**Key Dependencies:**
```txt
Flask==3.1.0
playwright==1.48.0
pdfplumber==0.11.4
python-dotenv==1.0.1
```

**Browser Requirements:**
- Microsoft Edge (for Rogers)
- Chromium (installed via Playwright)

---

## Deployment Architecture

### Current Deployment
```
┌─────────────────────────────────────┐
│   Local Development Machine         │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  Flask Server (port 5000)   │   │
│   │  - Web interface            │   │
│   │  - Job manager              │   │
│   │  - Background threads       │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  Browser Automation         │   │
│   │  - Edge (Rogers)            │   │
│   │  - Chromium (others)        │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  File System                │   │
│   │  - ITC/invoices/            │   │
│   │  - ITC/logs/                │   │
│   │  - .env (credentials)       │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘
           │              │
           │              └─────────────→ SMTP Server
           │                              (Email delivery)
           └────────────────────────────→ Vendor Portals
                                          (Rogers, etc.)
```

### Production Deployment Target
```
┌─────────────────────────────────────────────────┐
│   Internal Server / VM                          │
│                                                 │
│   ┌─────────────────────────────────────────┐   │
│   │  Flask Application (WSGI server)        │   │
│   │  - Gunicorn or uWSGI                    │   │
│   │  - Auto-restart on failure              │   │
│   └─────────────────────────────────────────┘   │
│                                                 │
│   ┌─────────────────────────────────────────┐   │
│   │  IT-Managed Credentials                 │   │
│   │  - Vault or env vars                    │   │
│   │  - Automatic rotation                   │   │
│   └─────────────────────────────────────────┘   │
│                                                 │
│   ┌─────────────────────────────────────────┐   │
│   │  Optional: Reverse Proxy (nginx)        │   │
│   │  - HTTPS termination                    │   │
│   │  - Load balancing (if needed)           │   │
│   └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
           │
           └─→ Internal Network
               (Accessible to AP team)
```

---

## Monitoring and Observability

### Current Monitoring

**Logs:**
- File-based logs in `ITC/logs/`
- One log file per vendor run
- Timestamped entries with log levels

**Screenshots:**
- Captured at key automation steps
- Captured on all errors
- Named with step and timestamp

**Email notifications:**
- Success/failure report after each batch
- Lists completed and failed downloads

### Production Monitoring Recommendations

**Health checks:**
```python
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'version': '1.0.0'}
```

**Metrics to track:**
- Job success rate (%)
- Average download time per vendor
- Error frequency by type
- Email delivery success rate

**Alerting triggers:**
- Job failure rate > 25%
- Same vendor failing repeatedly (3+ times)
- Email delivery failures
- No successful jobs in 7 days (if scheduled)

---

## Testing Strategy

### Current Testing Approach

**Manual testing:**
- Command-line interface for vendor isolation
- Web interface for end-to-end testing
- Real vendor portals (no mocks)

**Testing workflow:**
```bash
# Test single account
python orchestrator.py rogers 0

# Check logs
tail ITC/logs/rogers_*.log

# Check screenshots
ls ITC/logs/*.png

# Test web interface
python web_app.py
# Open http://localhost:5000 in browser
```

### Future Testing Enhancements

**Unit tests:**
```python
# Test file naming
def test_generate_filename():
    downloader = RogersDownloader()
    date = datetime(2025, 12, 15)
    filename = downloader.generate_file_name(0, date)
    assert filename == "ROGE04_7803_15-Dec-2025_68050-YYT-16-412.pdf"

# Test date extraction
def test_extract_date():
    downloader = RogersDownloader()
    date = downloader.extract_date_from_pdf(
        'test_invoice.pdf',
        (130, 80, 210, 95),
        '%b %d, %Y'
    )
    assert date.year == 2025
```

**Integration tests:**
- Mock vendor responses with Playwright
- Test error handling paths
- Verify email sending

---

## Known Limitations

### Current Constraints

1. **Single concurrent job**
   - Only one download job can run at a time
   - Additional requests blocked until completion
   - Prevents resource conflicts and vendor issues

2. **Rogers requires visible browser**
   - Edge doesn't support headless mode
   - Browser window appears during Rogers downloads
   - Not suitable for completely headless environments

3. **No job persistence**
   - Jobs lost if server restarts
   - No historical job records
   - Progress lost on crash (must restart)

4. **No user authentication**
   - Open access to anyone on network
   - Designed for internal deployment only
   - Not suitable for public internet

5. **Two-factor authentication (2FA) not supported**
   - Vendors with 2FA require manual intervention
   - Enmax and Eastward implementations incomplete due to 2FA
   - May need API access instead of portal automation

### Workarounds

**For 2FA vendors:**
- Request vendor disable 2FA for automation account
- Use dedicated API if vendor provides one
- Implement manual intervention step

**For concurrent jobs:**
- Run on separate servers if needed
- Or accept sequential processing

---

## Future Roadmap

### Phase 1: Current (Complete)
- ✅ Base architecture with inheritance pattern
- ✅ Rogers, Manitoba Hydro, Halifax Water implementations
- ✅ Web interface with progress tracking
- ✅ Batch email delivery
- ✅ PDF date extraction

### Phase 2: Production Deployment (In Progress)
- 🔄 Transfer to internal server
- 🔄 IT credential management
- 🔄 User training and documentation

### Phase 3: Enhancement (Future)
- ⏳ Add 5-7 additional vendors
- ⏳ User authentication
- ⏳ Scheduled execution (cron)
- ⏳ Job history database

### Phase 4: Scale (Future)
- ⏳ Multi-account session reuse
- ⏳ Parallel vendor processing
- ⏳ Advanced error recovery
- ⏳ Metrics and monitoring dashboard

---

## Additional Resources

**Related Documentation:**
- [README.md](README.md) - Project overview and quick start
- [ADDING_VENDORS.md](ADDING_VENDORS.md) - Step-by-step vendor implementation guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [DECISIONS.md](DECISIONS.md) - Detailed design decision log

**External References:**
- [Playwright Documentation](https://playwright.dev/python/docs/intro)
- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)
- [Flask Documentation](https://flask.palletsprojects.com/)

**Code Examples:**
- `ITC/downloaders/base.py` - Base class implementation
- `ITC/downloaders/rogers.py` - Complex vendor with bot detection
- `ITC/downloaders/halifaxwater.py` - Multi-account dropdown handling
- `ITC/downloaders/mhydro.py` - Custom date parsing example