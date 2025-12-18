"""
Email Notification System
Sends Invoice PDFs as email attachments
"""

import os
import logging
import smtplib

from pathlib import Path
from email import encoders
from dotenv import load_dotenv

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class EmailNotifier:
    """
    Handles sending invoice PDF's via email
    """

    def __init__(self):
        """ Initialize email configuration from .env """
        self.smtp_server = os.getenv('EMAIL_SMTP_SERVER')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', 587))
        self.username = os.getenv("EMAIL_USERNAME")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.from_email = os.getenv("EMAIL_FROM")
        default_recipients_str = os.getenv("EMAIL_TO", "")

        # Clean up whitespace in recipient list
        if default_recipients_str:
            self.default_recipients = [r.strip() for r in default_recipients_str.split(',') if r.strip()]
        else:
            self.default_recipients = []

        # Validate configuration
        if not all([self.smtp_server, self.smtp_port, self.username, self.password, self.default_recipients]):
            raise ValueError("Email credentials not configured in .env file")
    
    def send_invoice(self, invoice_path, recipients=None):
        """
        Send invoice PDF as email attachment

        ONLY sends if download was successful

        Args:
            invoice_path: Path to downloaded invoice PDF (string or Path)
            recepients: Optional list of email addresses (Uses EMAIL_TO from .env if None)

        Returns:
            bool: True if email was sent successfully, False otherwise
        """

        invoice_path = Path(invoice_path)

        # Use provided recipients or default from .env
        recipients = recipients or self.default_recipients

        if not recipients:
            logger.warning("No email recipients configured")
            return False
        
        # Verify file exists
        if not invoice_path.exists():
            logger.error(f"Invoice file not found: {invoice_path}")
            return False
        try:
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"Invoice: {invoice_path.name}"

            # Attach the PDF
            with open(invoice_path, 'rb') as file:
                part = MIMEBase('application', 'pdf')
                part.set_payload(file.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={invoice_path.name}'
            )

            msg.attach(part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Email sent to {', '.join(recipients)}: {invoice_path.name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False
        
    def send_batch_invoices(self, invoice_paths, recipients=None, job_results=None):
        """
        Send multiple invoice PDFs in a single email

        Args:
            invoice_paths: List of paths to download invoice PDFs
            recipients: Optional list of email addresses (Uses EMAIL_TO from .env if None)

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        
        if not invoice_paths and not job_results:
            logger.warning("No invoice files to send")
            return False
        
        # Use provided recipient or default from .env
        recipients = recipients or self.default_recipients

        if not recipients:
            logger.warning("No email recipients configured")
            return False
        
        # Verify all files exist
        valid_paths = []
        for invoice_path in invoice_paths:
            invoice_path = Path(invoice_path)
            if invoice_path.exists():
                valid_paths.append(invoice_path)
            else:
                logger.warning(f"Invoice file not found: {invoice_path}")

        if not valid_paths and not job_results:
            logger.error("No valid invoice files to send")
            return False
        
        try:
            from email.mime.text import MIMEText

            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)

            # Subject line with count
            success_count = len(valid_paths)

            # Count failures if job_results provided
            failed_count = 0
            if job_results:
                failed_count = len([r for r in job_results if r.get('status') == 'failed'])

            if failed_count > 0:
                msg['Subject'] = f"Batch Invoice Download - {success_count} succeeded, {failed_count} failed"

            else:
                msg['Subject'] = f"Batch Invoice Download - {success_count} invoice{'s' if success_count != 1 else '' }"

            # Create email body
            body_lines = []
            body_lines.append("Invoice Download Report")
            body_lines.append("=" * 60)
            body_lines.append("")

            # Summary
            body_lines.append(f"Successfully downloaded: {success_count}")
            if failed_count > 0:
                body_lines.append(f"Failed: {failed_count}")
            body_lines.append("")

            # List failures with details
            if job_results and failed_count > 0:
                body_lines.append("Failed Downloads:")
                body_lines.append("-" * 60)
                for result in job_results:
                    if result.get('status') == 'failed':
                        vendor = result.get('vendor', 'Unknown').upper()
                        account = result.get('account', '?')
                        error = result.get('error', 'Unknown error')
                        body_lines.append(f" x{vendor} - Account #{account + 1}")
                        body_lines.append(f"  Error: {error}")
                        body_lines.append("")
                
                body_lines.append("ACTION REQUIRED:")
                body_lines.append("Please manually download the failed invoices or re-run")
                body_lines.append("the automation for these accounts individually")
                body_lines.append("")

            body_lines.append("=" * 60)
            body_lines.append("This is an automated message from the Invoice Automation System")

            # Attach text body
            body_text = "\n".join(body_lines)
            msg.attach(MIMEText(body_text, 'plain'))
            
            # Attach all PDFs
            for invoice_path in valid_paths:
                with open(invoice_path, 'rb') as file:
                    part = MIMEBase('application', 'pdf')
                    part.set_payload(file.read())

                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={invoice_path.name}'
                )

                msg.attach(part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            filenames = ', '.join([p.name for p in valid_paths])
            logger.info(f"Batch email sent to {', '.join(recipients)}: {filenames}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send batch email: {e}", exc_info=True)
            return False

    def test_connection(self):
        """
        Test email configuration

        Returns:
            bool: True if connection successful
        """

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)

            logger.info(" Email connection successful")
            print(f"✅ Email connection successful!")
            print(f"   Server: {self.smtp_server}:{self.smtp_port}")
            print(f"   From: {self.from_email}")
            print(f"   To: {', '.join(self.default_recipients)}")
            return True
        
        except Exception as e:
            logger.error(f"Email connection failed: {e}")
            print(f" Email connection failed: {e}")
            return False
    
# Convenience function
def send_invoice_email(invoice_path, recepients=None):
    """
    Convenience function to send invoice via email

    Args:
        invoice_path: Path to invoice PDF
        recepients: Optional list of email addresses

    Returns:
        bool: True if successful
    """
    notifier = EmailNotifier()
    return notifier.send_invoice(invoice_path, recepients)


if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)

    notifer = EmailNotifier()

    # Test connection
    notifer.test_connection()