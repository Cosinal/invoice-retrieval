# ITC Invoice Downloader
*Automated system for downloading vendor invoices with standardized naming conventions*

## Overview
Previously, invoices were manually downloaded from multiple vendor portals, taking multiple hours every month
This system automated downloads across Rogers, and is scalable to more vendors.

This system was designed for Accounts Payable

---

## Quick Start

### Prerequisites
```bash
#Python version
Python 3.13+

# Required packages
pip install -r requirements.txt

# Install playwright browsers
playwright install chromium
```

### Setup

1. Clone the repository
```bash
git clone [https://github.com/Cosinal/invoice-retrieval]
cd invoices-denise
```

2. Create `.env` file in project root:
```bash
DOWNLOAD_PATH=ITC/invoices

ROGERS_LOGIN_URL=https://www.rogers.com/consumer/self-serve/overview
ROGERS_USERNAME=your_email@company.com
ROGERS_PASSWORD=your_password
```

3. Run your first download:
```bash
python orchestrator.py rogers 0
```

---

## Usage

### Basic Commands

```bash
# Download invoice for Rogers account 1
python orchestrator.py rogers 0

# Download invoice for Rogers account 2
python orchestrator.py rogers 1

# Download invoice for Rogers account 3
python orchestrator.py rogers 2
```

### Command Format
```bash
python orchestrator.py
```

- `<vendor>`: Vendor name (e.g. `rogers`, `bell`, `telus`)
- `<account_index>`: Account number (0-indexed, so 0 = Account 1)


### Output
Downloaded invoices are saved to `ITC/invoices` with the format:
```bash
{vendor_number}_{account_number}_{date}_{gl_account}.pdf
```
**Components:**
- `vendor_number`: ITC vendor identifier (e.g., ROGE04)
- `account_number`: Vendor account number (e.g., 7803)
- `date`: Invoice date in `DD-MMM-YYYY` format (e.g., 12-Nov-2025)
- `gl_account`: General ledger account code (e.g., GL5100)

Example:
```bash
ROGE04_7803_12-Nov-2025_GL5100.pdf
```

Logs and screenshots are saved to `ITC/logs/` for debugging

---

## Project Structure
```bash
invoices-denise/
├── orchestrator.py           # Main CLI entry point
├── .env                      # Credentials (NOT in git)
├── ITC/
│   ├── downloaders/
│   │   ├── __init__.py
│   │   ├── base.py          # Base class - shared logic
│   │   ├── rogers.py        # Rogers-specific implementation
│   │   └── bell.py          # Bell-specific implementation (future)
│   ├── invoices/            # Downloaded PDFs saved here
│   ├── logs/                # Execution logs & screenshots
│   └── utils/
│       └── bbox_finder.py   # Tool for finding PDF coordinates
└── documents/
    ├── README.md            # This file
    ├── ARCHITECTURE.md      # System design documentation
    ├── ADDING_VENDORS.md    # Guide for adding new vendors
    └── TROUBLESHOOTING.md   # Common issues and fixes
```

---

## Supported Vendors
```bash
rogers
```

---

## Configuration

### Account Metadata
Account specific information (account numbers, GL codes) is stored in each vendor's download agent

```bash
# Account metadata for filename generation
    ACCOUNT_METADATA = {
        0: {'vendor_number': 'ROGE04', 'account_number': '3509', 'gl_account': '68050-YYT-11-410'}
```

---


