"""
Flask Web Application for Invoice Downloading
Simple dashbord for manual triggering
"""

import time
import threading

from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, jsonify, request

from orchestrator import VENDORS

app = Flask(__name__)

# Global state to track downloads
# Format: {vendor_account_key: {'status': 'ready/downloading/done/error', 'message': str}}
download_state = {}

# Lock to prevent concurrent downloads of same account
download_locks = {}

def get_last_download_time(vendor_name, account_index):
    """
    Check when this account was last downloaded

    Returns:
        datetime or None
    """

    downloader = VENDORS[vendor_name]
    metadata = downloader.ACCOUNT_METADATA[account_index]

    # Look for most recent file for this account
    invoice_dir = Path("ITC/invoices")
    account_number = metadata['account_number']
    vendor_number = metadata['vendor_number']

    # Find files matching this account
    pattern = f"{vendor_number}_{account_number}_*.pdf"
    files = list(invoice_dir.glob(pattern))

    if not files:
        return None
    
    # Get the most recent file
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    return datetime.fromtimestamp(latest_file.stat().st_mtime)

def format_time_ago(dt):
    """ 
    Format datetime as "X time ago"
    """

    if dt is None:
        return "Never"
    
    diff = datetime.now() - dt

    hours = int(diff.total_seconds() // 3600)
    minutes = int((diff.total_seconds() % 3600) // 60)

    if hours == 0 and minutes == 0:
        return "Just now"
    elif hours == 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif minutes == 0:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        return f"{hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''} ago"
    

def run_download_background(vendor_name, account_index):
    """
    Run the download in a background thread
    Updates download_state as it progresses
    """

    key = f"{vendor_name}_{account_index}"

    try:
        download_state[key] = {
            'stauts': 'downloading',
            'message': 'Starting download...',
            'started': time.time()
        }

        # Import email notifier
        from ITC.integrations.email_notifier import send_invoice_email

        # Run download
        downloader = VENDORS[vendor_name]
        result = downloader.run(
            account_index=account_index,
            download_path="ITC/invoices",
            headless=True # Run in background
        )

        if result:
            # Success! Send email
            invoice_file = Path(result)

            download_state[key] = {
                'status': 'emailing',
                'message': 'Sending email...',
                'started': download_state[key]['started']
            }

            email_sent = send_invoice_email(invoice_file)

            if email_sent:
                download_state[key] = {
                    'status': 'done',
                    'message': f'Done! ({invoice_file.name})',
                    'started': download_state[key]['started'],
                    'filename': invoice_file.name
                }
            else:
                download_state[key] = {
                    'status': 'done',
                    'message': f'Downloaded but failed to send email. ({invoice_file.name})',
                    'started': download_state[key]['started'],
                    'filename': invoice_file.name
                }
        else:
            download_state[key] = {
                'status': 'error',
                'message': 'Download failed - Check logs',
                'started': download_state[key]['started']
            }
    except Exception as e:
        download_state[key] = {
            'status': 'error',
            'message': f'Error: {str(e)[:100]}',
            'started': download_state.get(key, {}).get('started', time.time())
        }

    finally:
        # Release lock
        if key in download_locks:
            del download_locks[key]



@app.route("/")
def index():
    """
    Main Dashboard Page
    """

    # Build vendor data with last download times
    vendor_data = {}
    
    for vendor_name, downloader in VENDORS.items():
        accounts = []
        
        for i in range(downloader.max_accounts):
            last_download = get_last_download_time(vendor_name, i)
            
            accounts.append({
                'index': i,
                'number': downloader.ACCOUNT_METADATA[i]['account_number'],
                'last_download': format_time_ago(last_download)
            })
        
        vendor_data[vendor_name] = {
            'name': vendor_name.upper(),
            'accounts': accounts,
            'total_accounts': len(accounts)
        }
    
    return render_template('index.html', vendors=vendor_data)


@app.route('/download', methods=['POST'])
def download():
    """Start download for specific account"""
    
    data = request.json
    vendor_name = data.get('vendor')
    account_index = data.get('account_index')
    
    if vendor_name not in VENDORS:
        return jsonify({'error': 'Invalid vendor'}), 400
    
    key = f"{vendor_name}_{account_index}"
    
    # Check if already downloading
    if key in download_locks:
        return jsonify({'error': 'Already downloading this account'}), 409
    
    # Set lock
    download_locks[key] = True
    
    # Start download in background thread
    thread = threading.Thread(
        target=run_download_background,
        args=(vendor_name, account_index),
        daemon=True
    )
    thread.start()
    
    return jsonify({'message': 'Download started', 'key': key})


@app.route('/download-all', methods=['POST'])
def download_all():
    """
    Download all accounts for a vendor sequentially
    """
    
    data = request.json
    vendor_name = data.get('vendor')
    
    if vendor_name not in VENDORS:
        return jsonify({'error': 'Invalid vendor'}), 400
    
    downloader = VENDORS[vendor_name]
    
    # Start downloads sequentially in background thread
    def download_all_sequential():
        for i in range(downloader.max_accounts):
            key = f"{vendor_name}_{i}"
            
            # Skip if already downloading
            if key in download_locks:
                continue
            
            # Set lock and download
            download_locks[key] = True
            run_download_background(vendor_name, i)
            
            # Wait a bit between downloads
            time.sleep(2)
    
    thread = threading.Thread(target=download_all_sequential, daemon=True)
    thread.start()
    
    return jsonify({'message': f'Downloading all {downloader.max_accounts} accounts'})

@app.route('/status/<vendor>/<int:account_index>')
def status(vendor, account_index):
    """Get current status of a download"""
    
    key = f"{vendor}_{account_index}"
    
    # Return 'ready' if no state exists yet
    if key not in download_state:
        return jsonify({
            'status': 'ready',
            'message': 'Ready to download'
        })
    
    state = download_state[key]
    
    # Safely check for status key
    if 'status' not in state:
        return jsonify({
            'status': 'ready',
            'message': 'Ready to download'
        })
    
    # Calculate elapsed time if downloading
    if state['status'] == 'downloading' and 'started' in state:
        elapsed = int(time.time() - state['started'])
        return jsonify({
            'status': state['status'],
            'message': f"{state.get('message', 'Downloading...')} ({elapsed}s)",
            'elapsed': elapsed
        })
    
    return jsonify(state)

@app.route('/reset/<vendor>/<int:account_index>', methods=['POST'])
def reset(vendor, account_index):
    """Reset status back to 'ready'"""
    
    key = f"{vendor}_{account_index}"
    
    if key in download_state:
        del download_state[key]
    
    if key in download_locks:
        del download_locks[key]
    
    return jsonify({'message': 'Reset to ready'})

if __name__ == '__main__':
    print("="*70)
    print("Starting ITC Invoice Downloader Web Interface")
    print("="*70)
    print()
    print("Open in browser: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print()
    print("="*70)
    
    app.run(debug=True, host='0.0.0.0', port=5000)