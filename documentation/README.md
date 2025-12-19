# 📄 Invoice Automation System

Automated invoice downloader for vendor business accounts with standardized file naming and web-based interface.

![Python](https://img.shields.io/badge/python-3.13+-blue.svg)
![Status](https://img.shields.io/badge/status-production--ready-success.svg)

---

## What It Does

Automates invoice retrieval from vendor portals through a web interface. Click one button, receive standardized invoices via email within 2-5 minutes.

**Example filename:**
```
ROGE04_7803_15-Dec-2025_68050-YYT-16-412.pdf
```

**Time saved:** 4 hours monthly vs manual process

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Credentials
Copy `.env-example` to `.env` and fill in credentials:
```env
DOWNLOAD_PATH=ITC/invoices

# Rogers
ROGERS_LOGIN_URL=https://www.rogers.com/consumer/self-serve/overview
ROGERS_USERNAME=your_email@company.com
ROGERS_PASSWORD=your_password

# Email Configuration
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@company.com
```

### 3. Start Web Interface
```bash
python web_app.py
```
Open `http://localhost:5000` in your browser

---

## Current Vendors

- **Rogers** (3 accounts) 
- **Manitoba Hydro** (1 account) 
- **Halifax Water** (2 accounts) 

**Total:** 6 accounts across 3 vendors

---

## Usage

### Web Interface (Recommended)
```bash
python web_app.py
```
- Navigate to `http://localhost:5000`
- Click "Download All Invoices" for batch processing
- Or click individual account buttons for single downloads
- Real-time progress tracking
- Email delivery with success/failure reports

### Command Line (Testing)
```bash
# Download single invoice
python orchestrator.py rogers 0

# Where:
#   rogers = vendor name
#   0 = account index (0-based)
```

---

## Project Structure
```
invoices-denise/
├── web_app.py                  # Web interface (main entry point)
├── orchestrator.py             # CLI testing tool
├── batch_download.py           # Legacy batch script
├── .env                        # Credentials (gitignored)
├── .env-example                # Template for credentials
├── requirements.txt            # Python dependencies
├── static/
│   └── index.html              # Web dashboard frontend
├── ITC/
│   ├── downloaders/
│   │   ├── base.py            # Base downloader class
│   │   ├── rogers.py          # Rogers implementation
│   │   ├── mhydro.py          # Manitoba Hydro implementation
│   │   └── halifaxwater.py    # Halifax Water implementation
│   ├── web/
│   │   └── job_manager.py     # Job tracking system
│   ├── integrations/
│   │   └── email_notifier.py  # Email delivery
│   ├── utils/
│   │   └── bbox_finder.py     # PDF date coordinate finder
│   ├── invoices/              # Downloaded PDFs (gitignored)
│   └── logs/                  # Execution logs (gitignored)
└── documentation/
    ├── README.md              # This file
    ├── ARCHITECTURE.md        # System design
    ├── ADDING_VENDORS.md      # How to add vendors
    ├── TROUBLESHOOTING.md     # Common issues
    └── DECISIONS.md           # Design decisions
```

---

## Features

**Automation:**
- One-click batch downloads or individual account selection
- Automatic login and navigation through vendor portals
- PDF date extraction for accurate invoice naming
- Sequential processing to avoid vendor security triggers

**Reliability:**
- Automatic retry logic for transient errors
- Bot detection recovery (Rogers RC01 handling)
- Comprehensive logging and debugging screenshots
- Collision prevention (one job at a time)

**User Experience:**
- Real-time progress tracking in web interface
- Email delivery with batch results and failure reports
- Persistent user settings for default email addresses
- Individual account buttons with GL code display

---

## File Naming Convention

Format: `VENDOR_ACCOUNT_DATE_GL-CODE.pdf`

**Components:**
- `VENDOR`: 6-character vendor code (e.g., ROGE04, MANI03, HALI01)
- `ACCOUNT`: Last 4 digits of vendor account number
- `DATE`: Invoice date in DD-MMM-YYYY format (extracted from PDF)
- `GL-CODE`: General ledger account code

**Example:**
```
ROGE04_7803_15-Dec-2025_68050-YYT-16-412.pdf
│      │     │           └─ GL account code
│      │     └─ Invoice date (from PDF)
│      └─ Account number
└─ Vendor code
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [🏗️ ARCHITECTURE.md](documentation/ARCHITECTURE.md) | System design and data flow |
| [➕ ADDING_VENDORS.md](documentation/ADDING_VENDORS.md) | Adding new vendors or accounts |
| [🐛 TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md) | Common issues and solutions |
| [📋 DECISIONS.md](documentation/DECISIONS.md) | Technical decisions and rationale |

---

## Requirements

- **Python 3.13+**
- **Microsoft Edge** (for Rogers downloads)
- **Chromium** (installed via Playwright)
- **Network access** to vendor portals and SMTP server

---

## Deployment Notes

**Current State:**
- Runs locally on development machine
- Browser-based interface at `http://localhost:5000`
- No authentication (internal network only)

**Production Deployment:**
- Host on internal server accessible to AP team
- Transfer credentials to IT-managed storage
- Configure internal DNS entry
- See executive summary for full deployment requirements

---

## Troubleshooting

**Common Issues:**

- **Timeout errors:** Vendor website changed selectors → See TROUBLESHOOTING.md
- **Rogers RC01 errors:** Bot detection triggered → System auto-recovers
- **Date extraction fails:** PDF format changed → Use `bbox_finder.py` to find new coordinates
- **Email not sending:** Check SMTP credentials in `.env`

For detailed troubleshooting, see [TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md)

---

## Contributing

When adding new vendors:
1. Create vendor file in `ITC/downloaders/`
2. Implement three methods: `login()`, `navigate_to_invoices()`, `download_invoice()`
3. Use `bbox_finder.py` to find PDF date coordinates
4. Register vendor in `web_app.py`
5. Test via CLI then web interface

See [ADDING_VENDORS.md](documentation/ADDING_VENDORS.md) for detailed guide.

---

## License

Internal use only - The Inland Group of Companies

---

## Support

For questions or issues:
- Check [TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md)
- Review logs in `ITC/logs/`
- Contact development team