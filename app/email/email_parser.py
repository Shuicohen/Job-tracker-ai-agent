"""
Email fetching and parsing functionality
"""
import imaplib
import email
from email.header import decode_header
from app.config.settings import EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER, logger

def fetch_linkedin_emails():
    """
    Fetch LinkedIn job notification emails (including read emails).
    Returns a list of dictionaries containing email subject and body.
    """
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        
        # Login using credentials from settings
        if not all([EMAIL_ADDRESS, EMAIL_PASSWORD]):
            logger.error("Email credentials not properly configured")
            return []
            
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        # Select the INBOX
        mail.select('INBOX')
        
        # Search for all emails from LinkedIn jobs (not just unread ones)
        # Modified to include read emails and emails from the past
        status, messages = mail.search(None, 'FROM "jobs-noreply@linkedin.com"')
        
        if status != 'OK':
            logger.error("Failed to search emails")
            return []
            
        # Get the email IDs
        email_ids = messages[0].split()
        
        # Limit to latest 20 emails to avoid processing too many at once
        email_ids = email_ids[-20:] if len(email_ids) > 20 else email_ids
        
        logger.info(f"Found {len(email_ids)} LinkedIn job emails to process")
        print(f"Found {len(email_ids)} LinkedIn job emails to process")
        
        emails = []
        
        for email_id in email_ids:
            # Fetch the email
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                logger.error(f"Failed to fetch email {email_id}")
                continue
                
            # Parse the email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Get subject
            subject = decode_header(email_message['subject'])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode(errors='replace')
                
            # Get body
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            try:
                                body = payload.decode(errors='replace')
                            except Exception as e:
                                logger.error(f"Error decoding email body: {str(e)}")
                                body = str(payload)
                        break
            else:
                payload = email_message.get_payload(decode=True)
                if payload:
                    try:
                        body = payload.decode(errors='replace')
                    except Exception as e:
                        logger.error(f"Error decoding email body: {str(e)}")
                        body = str(payload)
                
            emails.append({
                'subject': subject,
                'body': body
            })
            
        # Close the connection
        mail.close()
        mail.logout()
        
        logger.info(f"Successfully fetched {len(emails)} LinkedIn emails")
        return emails
        
    except Exception as e:
        logger.error(f"Error fetching LinkedIn emails: {str(e)}")
        return [] 