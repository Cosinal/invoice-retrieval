"""
Flask Web Server for Invoice Automation
Stage 1: Basic job creation and status checking
"""

import os
import json
import threading
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, request
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

# Headless mode
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'

def validate_email(email):
    """  
    Lightweight email validation
    Returns (is_valid, cleaned_email, error_message)
    """
    if not email:
        return True, None, None # Empty is okay (will use default)
    
    # Strip whitespace
    email = email.strip()

    # Check if empty after stripping
    if not email:
        return True, None, None
    
    # Basic validation: must contain @ and . after @
    if '@' not in email:
        return False, None, "Email must contain '@'"
    
    local, domain = email.rsplit('@', 1)

    if not local:
        return False, None, "Email must have characters before '@'"
    
    if '.' not in domain:
        return False, None, "Email domain must contain '.'"
    
    if domain.startswith('.') or domain.endswith('.'):
        return False, None, "Email domain cannot start or end with '.'"
    
    return True, email, None

# Vendor Configuration
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

def run_automation_job(job_id):
    """
    Background task that runs all downloaders
    Updates job state as it progresses
    Sends ONE email at the end with all downloaded invoices

    Supports two modes:
    - "all": Run all vendors and accounts
    - "single": Run one specific vendor / account
    """

    # Track successful downloads for batch email
    downloaded_files = []


    try:
        # Mark job as started
        job_manager.mark_started(job_id)

        # Get job to read metadata
        job = job_manager.get_jobs(job_id)
        metadata = job.metadata
        mode = metadata.get('mode', 'all')

        # Determine what to run based on mode
        if mode == 'single':
            # Single vendor/account mode
            vendor_name = metadata.get('vendor')
            account_index = metadata.get('account')

            if not vendor_name or account_index is None:
                raise ValueError("Single mode requires vendor and account in metadata")
            
            if vendor_name not in VENDORS:
                raise ValueError(f"Unknown vendor: {vendor_name}")
            
            # Create jobs list with just this one account
            jobs_to_run = [(vendor_name, VENDORS[vendor_name], account_index)]
            total_accounts = 1
        
        else:
            # "all" mode - run everything
            jobs_to_run = []
            for vendor_name, vendor_config in VENDORS.items():
                num_accounts = vendor_config['accounts']
                for account_index in range(num_accounts):
                    jobs_to_run.append((vendor_name, vendor_config, account_index))
            total_accounts = len(jobs_to_run)

        job_manager.update_job(job_id, total_accounts=total_accounts)

        # Run each job
        for vendor_name, vendor_config, account_index in jobs_to_run:
            downloader_class = vendor_config['class']
            downloader = downloader_class()

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
                    headless = HEADLESS_MODE
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
                email_to = job.metadata.get('email_to') # Get email override from metadata

                email_notifier.send_batch_invoices(
                    downloaded_files,
                    job_results=job.results, # Pass all results including failures
                    recipients=[email_to] if email_to else None # Use override or default
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
    Accepts JSON body with optional parameters
    - mode: "all" or "single" (default: "all")
    - vendor: vendor name (required if mode = "single")
    - account: account index (required if mode = "single")
    - email_to: email override (optional, falls back to .env default)

    Returns: job_id to track process
    """

    # Check if a job is already running
    if job_manager.has_active_job():
        return jsonify({
            'success': False,
            'error': 'A job is already running. Please wait for it to complete'
        }), 409

    # Parse JSON body
    data = request.get_json() or {}

    mode = data.get('mode', 'all')
    vendor = data.get('vendor')
    account = data.get('account')
    email_to = data.get('email_to')

    # Validate Email
    is_valid, cleaned_email, error_msg = validate_email(email_to)
    if not is_valid:
        return jsonify({
            'success': False,
            'error': f'Invalid email address: {error_msg}'
        }), 400
    
    email_to = cleaned_email

    if not email_to:
        user_settings = load_user_settings('local')
        email_to = user_settings.get('default_email_to')

    # Validate mode
    if mode not in ['all', 'single']:
        return jsonify({
            'success': False,
            'error': f'Invalid mode: {mode}, must be "all" or "single"'
        }), 400
    
    # Validate single mode parameters
    if mode == 'single':
        if not vendor:
            return jsonify({
                'success': False,
                'error': 'vendor is required when mode is "single"'
            }), 400
        
        if vendor not in VENDORS:
            return jsonify({
                'success': False,
                'error': f'Unknown vendor: {vendor}'
            }), 400
        
        if account is None:
            return jsonify({
                'success': False,
                'error': 'account is required when mode is "single"'
            }), 400
        
        # Validate account index
        max_accounts = VENDORS[vendor]['accounts']
        if not (0 <= account < max_accounts):
            return jsonify({
                'success': False,
                'error': f'Invalid account index {account} for {vendor}. Must be 0-{max_accounts - 1}'
            }), 400
        
    # Create job metadata
    metadata = {
        'mode': mode,
        'vendor': vendor,
        'account': account,
        'email_to': email_to,
        'requested_by': 'local' # Auth-ready: will become real user_id later
    }

    # Create a new job with metadata
    job = job_manager.create_job(metadata=metadata)

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
        'message': 'Job started',
        'mode': mode
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

@app.route('/api/vendors', methods=['GET'])
def get_vendors():
    """  
    Get list of available vendors and their account counts
    Used by frontend to render individual download buttons
    """

    vendors_list = []

    for vendor_name, vendor_config in VENDORS.items():
        num_accounts = vendor_config['accounts']
        vendors_list.append({
            'name': vendor_name,
            'display_name': vendor_name.upper(),
            'accounts': list(range(num_accounts)) # [0, 1, 2] instead of 3
        })
    
    return jsonify({
        'success': True,
        'vendors': vendors_list
    })


@app.route('/api/me', methods=['GET'])
def get_current_user():
    """   
    Get current user info and settings
    Auth-ready: Returns fake "local" user for now
    """

    # Load settings from file
    settings = load_user_settings('local')

    return jsonify({
        'success': True,
        'user': {
            'user_id': 'local',
            'name': 'Local User',
            'settings': settings
        }
    })


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """   
    Update user settings
    Auth-Ready: Updates fake "local" user for now
    """
    data = request.get_json() or {}

    existing_settings = load_user_settings('local')

    # Validate and merge new settings
    if 'default_email_to' in data:
        email = data['default_email_to']
        is_valid, cleaned_email, error_msg = validate_email(email)

        if not is_valid:
            return jsonify({
                'success': False,
                'error': f'Invalid email address: {error_msg}'
            }), 400
        
        existing_settings['default_email_to'] = cleaned_email

    # Save merged settings
    save_user_settings('local', existing_settings)

    return jsonify({
        'success': True,
        'settings': existing_settings
    })

# Helper functions for setting storage

def load_user_settings(user_id):
    """ Load user settings from JSON file """
    settings_file = Path('settings.json')

    if not settings_file.exists():
        return {}
    
    try:
        with open(settings_file, 'r') as f:
            all_settings = json.load(f)
            return all_settings.get(user_id, {})
    except:
        return {}
    

def save_user_settings(user_id, settings):
    """ Save user settings to JSON file """
    settings_file = Path('settings.json')

    # Load existing settings
    all_settings = {}
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                all_settings = json.load(f)
        except:
            pass

    # Update all settings for this user
    all_settings[user_id] = settings

    # Save back to file
    with open(settings_file, 'w') as f:
        json.dump(all_settings, f, indent=2)


if __name__ == '__main__':
    print("=" * 60)
    print("Invoice Automation Web Interface")
    print("=" * 60)
    print("Starting server on http://localhost:5000")
    print("Open this URL in your browser to access the dashboard")
    print("=" * 60)

    app.run(debug=True, port=5000)
