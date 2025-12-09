# 📄 ITC Invoice Downloader

Automated invoice downloader for Rogers, Bell, and Telus business accounts with standardized file naming.

![Python](https://img.shields.io/badge/python-3.13+-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

---

## What It Does

Downloads vendor invoices automatically and saves them with standardized naming:
```bash
ROGE04_7803_12-Dec-2025_68050-YYT-11-410.pdf
```

Saves **2+ hours monthly** vs manual downloads.

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright -m install chromium
```

### 2. Configure Credentials
Create `.env` in project root:
```env
DOWNLOAD_PATH=ITC/invoices

ROGERS_LOGIN_URL=https://www.rogers.com/consumer/self-serve/overview
ROGERS_USERNAME=your_email@company.com
ROGERS_PASSWORD=your_password
```

### 3. Download Your First Invoice
```bash
python orchestrator.py rogers 0
```

---

## Project Structure
```
invoices-denise/
├── orchestrator.py              # Main entry point
├── .env                         # Credentials (gitignored)
├── ITC/
│   ├── downloaders/
│   │   ├── base.py             # Base downloader class
│   │   └── rogers.py           # Rogers implementation
│   ├── invoices/               # Downloaded PDFs
│   ├── logs/                   # Execution logs & screenshots
│   └── utils/                  # case-specific tools
└── documents/
    ├── README.md               # This file
    ├── ARCHITECTURE.md         # System design
    ├── ADDING_VENDORS.md       # How to add vendors
    └── TROUBLESHOOTING.md      # How to fix issues
```

---

## Documentation
## Documentation

| Document | When to Read |
|----------|--------------|
| [🏗️ ARCHITECTURE.md](documentation/ARCHITECTURE.md) | Understanding how the system works |
| [➕ ADDING_VENDORS.md](documentation/ADDING_VENDORS.md) | Adding Bell, Telus, or new accounts |
| [🐛 TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md) | When something breaks |