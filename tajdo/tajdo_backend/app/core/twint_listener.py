import imaplib
import email
import re
import asyncio
import logging
import ssl
from email.header import decode_header
from sqlalchemy.orm import Session
from ..db.session import engine
from ..models import models
from ..core.config import settings
from ..services.email_service import EmailService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

email_service = EmailService()

async def start_twint_listener():
    """Background task to check for TWINT payment emails periodically."""
    logger.info("Starting TWINT email listener...")
    logger.info(f"   >>> Configuration Loaded: Server='{settings.IMAP_SERVER}' Port={settings.IMAP_PORT} User='{settings.TWINT_EMAIL_USER}'")
    while True:
        try:
            await asyncio.to_thread(check_emails)
        except Exception as e:
            logger.error(f"Error in TWINT listener: {e}")
        
        # Check every 60 seconds
        await asyncio.sleep(60)

def check_emails():
    """Connects to IMAP, fetches unread TWINT emails, and updates orders."""
    mail = None
    try:
        if "actual_password" in settings.TWINT_EMAIL_PASSWORD or not settings.TWINT_EMAIL_PASSWORD:
            logger.warning("TWINT_EMAIL_PASSWORD is not set correctly in .env. Skipping email check.")
            return

        # Connect to IMAP
        logger.info(f"Connecting to IMAP server: {settings.IMAP_SERVER} on port {settings.IMAP_PORT}")
        
        if settings.IMAP_PORT == 993:
            mail = imaplib.IMAP4_SSL(settings.IMAP_SERVER, port=settings.IMAP_PORT, timeout=30)
        else:
            logger.info(f"Connecting to port {settings.IMAP_PORT} (STARTTLS mode)...")
            mail = imaplib.IMAP4(settings.IMAP_SERVER, port=settings.IMAP_PORT, timeout=30)
            
            # Upgrade connection to SSL
            ssl_context = ssl.create_default_context()
            mail.starttls(ssl_context=ssl_context)
            
        logger.info(f"Logging in with user: {settings.TWINT_EMAIL_USER}")
        mail.login(settings.TWINT_EMAIL_USER, settings.TWINT_EMAIL_PASSWORD)
        mail.select("inbox")

        # Search for UNSEEN emails from the specific TWINT sender
        status, messages = mail.search(None, '(UNSEEN FROM "no-reply@twintpay.ch")')
        
        if status != "OK" or not messages[0]:
            return

        for num in messages[0].split():
            try:
                # Fetch the email
                res, msg_data = mail.fetch(num, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        # Extract plain text body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()

                        # Parse Order ID (Looking for pattern "ORD-xxxxxx")
                        match = re.search(r"(ORD-[A-F0-9]{6})", body, re.IGNORECASE)
                        if match:
                            order_number = match.group(1).upper() # Normalize to uppercase
                            logger.info(f"Found TWINT payment for order: {order_number}")
                            process_payment_confirmation(order_number)
                        else:
                            logger.warning("TWINT email received but no Order ID found in body.")
            except Exception as e:
                logger.error(f"Error processing email {num}: {e}")

    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP Authentication/Command Error: {e}")
        logger.error("Please verify TWINT_EMAIL_USER, TWINT_EMAIL_PASSWORD, and IMAP_SERVER in your .env file.")
    except ssl.SSLError as e:
        logger.error(f"SSL/TLS Error: {e}. Check if the server supports the configured encryption mode.")
    # except (ConnectionResetError, OSError) as e:
    #     logger.error(f"IMAP Connection Error to '{settings.IMAP_SERVER}': {e}")
    #     logger.error("The connection was forcibly closed. This is often caused by:")
    #     logger.error(f"1. Incorrect IMAP server address. You are trying to connect to: '{settings.IMAP_SERVER}'")
    #     logger.error("2. Antivirus software (Avast, AVG, etc.) blocking the script via 'Mail Shield'. Try disabling it temporarily.")
    #     logger.error("3. A firewall or VPN blocking port 993.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the IMAP listener: {e}")
    finally:
        if mail:
            try:
                if mail.state == 'SELECTED':
                    mail.close()
                mail.logout()
                logger.info("IMAP connection logged out and closed.")
            except Exception as e:
                logger.error(f"Error during IMAP logout: {e}")

def process_payment_confirmation(order_number: str):
    """Updates order status in the database and sends confirmation."""
    with Session(engine) as db:
        order = db.query(models.Order).filter(models.Order.order_number == order_number).first()
        
        if order and order.status == "pending_payment":
            order.status = "processing"
            db.commit()
            db.refresh(order)
            logger.info(f"Order {order_number} marked as paid (processing).")
            
            # Send the official confirmation email now that payment is received
            email_service.send_order_confirmation(order, order.user)