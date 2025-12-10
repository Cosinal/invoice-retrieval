"""
Flask Web Application for Invoice Downloading
Simple dashbord for manual triggering
"""

import threading

from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, jsonify, request

from orchestrator import VENDORS

app = Flask(__name__)

# Store Download Status
download_status = {}


def run_download_async(vendor_name, account_index):
    """ Run download in a background thread """

    key = f"{vendor_name}_{account_index}"
    download_status[key] = {'status': 'running', 'message': 'Download in progress...'}

    try:
        downloader = VENDORS[vendor_name]
        result = downloader.run(
            account_index=account_index,
            download_path=Path("ITC/invoices"),
            headless=True # Run headless in background
        )   

        if result:
            download_status[key] = {
                'status': 'success',
                'message': f"Downloaded: {Path(result).name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                'file': result
            }

        else:
            download_status[key] = {
                'status': 'failed',
                'message': 'Download failed. Check logs for details.'
            }
        
    except Exception as e:
        download_status[key] = {
            'status': 'error',
            'message': f"Error: {e}"
        }

@app.route('/')
def index():
    """ Main Dashboard Page """
    
    return render_template('index.html', vendors=VENDORS)

@app.route('download', methods=['POST'])
def download():
    """ Trigger download for specific account """

    data = request.json
    vendor_name = data.get('vendor')
    account_index = data.get('account_index')

    if vendor_name not in VENDORS:
        return jsonify({'error': 'Invalid vendor'}), 400
    
    # Run download in background thread
    thread = threading.Thread(
        target=run_download_async,
        args=(vendor_name, account_index)
    )
    thread.start()

    return jsonify({'message': 'Download started'})

@app.route('/status/<vendor>/<int:account_index>')
def status(vendor, account_index):
    """ Check Status of Download """

    key = f"{vendor}_{account_index}"
    return jsonify(download_status.get(key, {'status': 'idle'}))


@app.route('/recent')
def recent():
    """ Get recent downloads """

    invoice_dir = Path('ITC/invoices')
    files = sorted(
        invoice_dir.glob('*.pdf'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:10]  # Get 10 most recent files

    recent = [] 
    for f in files:
        recent.append({
            'name': f.name,
            'time': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'size': f'{f.stat().st_size / 1024:.1f} KB'
        })

    return jsonify(recent)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
