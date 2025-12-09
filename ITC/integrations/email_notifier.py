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