"""
Flask Web Server for Invoice Automation
Stage 1: Basic job creation and status checking
"""

import os
import threading
from flask import Flask, jsonify, send_from_directory
from dotenv import load_dotenv

from ITC.web.job_manager import job_manager
from ITC.integrations.email_notifier import EmailNotifier

from ITC.downloaders.rogers import RogersDownloader
from ITC.downloaders.mhydro import ManitobaHydroDownloader
from ITC.downloaders.halifaxwater import HalifaxWaterDownloader

# Load Email Instance
email_notifier = EmailNotifier()

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')

# Download path from environment
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH")

# Vendor Configuration
VENDORS = {
    'rogers': {
        'downloader': RogersDownloader(),
        'accounts': 3
    },
    'mhydro': {
        'downloader': ManitobaHydroDownloader(),
        'accounts': 1
    },
    'hwater': {
        'downloader': HalifaxWaterDownloader(),
        'accounts': 2
    }
}

def run_automation_job(job_id):
    """
    Background task that runs all downloaders
    Updates job state as it progresses
    Sends ONE email at the end with all downloaded invoices
    """

    # Track successful downloads for batch email
    downloaded_files = []


    try:
        # Mark job as started
        job_manager.mark_started(job_id)

        # Calculate total accounts
        total_accounts = sum(v['accounts'] for v in VENDORS.values())
        job_manager.update_job(job_id, total_accounts=total_accounts)

        # Run each vendor / account sequentially
        for vendor_name, vendor_config in VENDORS.items():
            downloader = vendor_config['downloader']
            num_accounts = vendor_config['accounts']

            for account_index in range(num_accounts):
                # Update current progress
                job_manager.update_job(
                    job_id,
                    current_vendor=vendor_name,
                    current_account=account_index
                )

                try:
                    # Run the downloader in headless mode
                    result = downloader.run(
                        account_index=account_index,
                        download_path = DOWNLOAD_PATH,
                        headless = True
                    )

                    # Record Result
                    if result:
                        job_manager.add_result(
                            job_id,
                            vendor=vendor_name,
                            account=account_index,
                            status='success',
                            filename=os.path.basename(result)
                        )
                        
                        # Add to email list
                        downloaded_files.append(result)
                    
                    else:
                        job_manager.add_result(
                            job_id,
                            vendor=vendor_name,
                            account=account_index,
                            status='failed',
                            error='Downloader returned None'
                        )
                
                except Exception as e:
                    # Record error for this account
                    job_manager.add_result(
                        job_id,
                        vendor=vendor_name,
                        account=account_index,
                        status='failed',
                        error=str(e)
                    )
            
        # Mark job as completed
        job_manager.mark_completed(job_id)

        # Send ONE email with all downloaded invoices
        if downloaded_files or any(r['status'] == 'failed' for r in job_manager.get_jobs(job_id).results):
            try:
                job = job_manager.get_jobs(job_id)
                email_notifier.send_batch_invoices(
                    downloaded_files,
                    job_results=job.results # Pass all results including failures
                )
            
            except Exception as e:
                # Log email error but don't fail the job
                print(f"Warning: Failed to send batch email: {e}")

    except Exception as e:
        # Job-level failure
        job_manager.mark_failed(job_id, str(e))


@app.route('/')
def index():
    """ Serve the main HTML page """
    return send_from_directory('static', 'index.html')

@app.route('/api/start-job', methods=['POST'])
def start_job():
    """ 
    Start a new automation job
    Returns job_id to track progress
    """

    # Create a job
    job = job_manager.create_job()

    # Start background thread
    thread = threading.Thread(
        target=run_automation_job,
        args=(job.job_id,),
        daemon=True
    )
    thread.start()

    return jsonify({
        'success': True,
        'job_id': job.job_id,
        'message': 'Job started'
    })

@app.route('/api/job-status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """
    Get current status of a job
    Frontend polls this endpoint every 2 seconds
    """
    job = job_manager.get_jobs(job_id)

    if not job:
        return jsonify({
            'success': False,
            'error': 'Job not found'
        }), 404
    
    return jsonify({
        'success': True,
        'job': job.to_dict()
    })


if __name__ == '__main__':
    print("=" * 60)
    print("Invoice Automation Web Interface")
    print("=" * 60)
    print("Starting server on http://localhost:5000")
    print("Open this URL in your browser to access the dashboard")
    print("=" * 60)

    app.run(debug=True, port=5000)
