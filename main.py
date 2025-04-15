import os
import csv
import logging
from datetime import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email
from email.header import decode_header
import json
import openai
import time

# Load environment variables
load_dotenv()

# Determine log directory (use /data if on Render)
log_dir = '/data/logs' if os.path.exists('/data') else 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'applications.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def extract_job_info(email_body):
    """
    Extract job information from email body using OpenAI GPT.
    Returns a dictionary with job details or None if extraction fails.
    """
    try:
        # Set OpenAI API key
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Prepare the prompt
        prompt = f"""
        Extract the following details from this job application confirmation email:

        - Job Title
        - Company Name
        - Application Status (e.g. Submitted, Viewed, Interview)
        - Date of Application

        Return ONLY valid JSON in this format:
        {{
          "title": "...",
          "company": "...",
          "status": "...",
          "date": "..."
        }}

        Email content:
        \"\"\"
        {email_body[:2000]}
        \"\"\"
        """
        
        # Call OpenAI API using the older version syntax which works
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts job application details from emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1  # Low temperature for more consistent output
        )
        
        # Extract and parse the JSON response
        json_str = response.choices[0].message['content'].strip()
        
        # Add error handling for possible JSON issues
        # Remove any markdown code blocks if present
        if json_str.startswith("```json"):
            json_str = json_str.replace("```json", "").replace("```", "").strip()
        elif json_str.startswith("```"):
            json_str = json_str.replace("```", "").strip()
            
        job_info = json.loads(json_str)
        
        logging.info(f"Successfully extracted job info: {job_info}")
        return job_info
        
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON response: {str(e)}")
        logging.error(f"JSON string was: {json_str if 'json_str' in locals() else 'Not available'}")
        return None
    except Exception as e:
        logging.error(f"Error extracting job info: {str(e)}")
        return None

def fetch_linkedin_emails():
    """
    Fetch LinkedIn job notification emails (including read emails).
    Returns a list of dictionaries containing email subject and body.
    """
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        
        # Login using credentials from .env
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        if not all([email_address, email_password]):
            logging.error("Email credentials not properly configured")
            return []
            
        mail.login(email_address, email_password)
        
        # Select the INBOX
        mail.select('INBOX')
        
        # Search for all emails from LinkedIn jobs (not just unread ones)
        # Modified to include read emails and emails from the past
        status, messages = mail.search(None, 'FROM "jobs-noreply@linkedin.com"')
        
        if status != 'OK':
            logging.error("Failed to search emails")
            return []
            
        # Get the email IDs
        email_ids = messages[0].split()
        
        # Limit to latest 20 emails to avoid processing too many at once
        email_ids = email_ids[-20:] if len(email_ids) > 20 else email_ids
        
        logging.info(f"Found {len(email_ids)} LinkedIn job emails to process")
        print(f"Found {len(email_ids)} LinkedIn job emails to process")
        
        emails = []
        
        for email_id in email_ids:
            # Fetch the email
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                logging.error(f"Failed to fetch email {email_id}")
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
                                logging.error(f"Error decoding email body: {str(e)}")
                                body = str(payload)
                        break
            else:
                payload = email_message.get_payload(decode=True)
                if payload:
                    try:
                        body = payload.decode(errors='replace')
                    except Exception as e:
                        logging.error(f"Error decoding email body: {str(e)}")
                        body = str(payload)
                
            emails.append({
                'subject': subject,
                'body': body
            })
            
        # Close the connection
        mail.close()
        mail.logout()
        
        logging.info(f"Successfully fetched {len(emails)} LinkedIn emails")
        return emails
        
    except Exception as e:
        logging.error(f"Error fetching LinkedIn emails: {str(e)}")
        return []

class JobApplicationTracker:
    def __init__(self):
        # Check if we're in render environment and use the mounted disk
        if os.path.exists('/data'):
            self.base_dir = '/data'
            # Create necessary directories in data volume
            if not os.path.exists(os.path.join(self.base_dir, 'logs')):
                os.makedirs(os.path.join(self.base_dir, 'logs'))
            if not os.path.exists(os.path.join(self.base_dir, 'company_research')):
                os.makedirs(os.path.join(self.base_dir, 'company_research'))
            self.csv_file = os.path.join(self.base_dir, 'job_applications.csv')
        else:
            self.base_dir = '.'
            self.csv_file = 'job_applications.csv'
        
        self._ensure_files_exist()
        
    def _ensure_files_exist(self):
        """Ensure required files and directories exist"""
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(self.base_dir, 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        # Create CSV file with headers if it doesn't exist
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'company', 'status', 'date', 'research'])
                writer.writeheader()
    
    def _is_duplicate(self, data):
        """
        Check if a job application already exists in the CSV file.
        
        Args:
            data (dict): Dictionary containing job application details
            
        Returns:
            bool: True if the application is a duplicate, False otherwise
        """
        try:
            existing_applications = self.get_all_applications()
            
            # Check if this exact application already exists
            for app in existing_applications:
                # Compare title and company as the key identifiers for duplicates
                if (app['title'].lower() == data['title'].lower() and 
                    app['company'].lower() == data['company'].lower()):
                    logging.info(f"Duplicate application found: {data['title']} at {data['company']}")
                    print(f"Duplicate application found: {data['title']} at {data['company']}")
                    return True
                    
            return False
        except Exception as e:
            logging.error(f"Error checking for duplicates: {str(e)}")
            return False  # Assume not a duplicate in case of error
    
    def _get_company_research(self, company):
        """
        Get company research from file or generate if it doesn't exist.
        
        Args:
            company (str): Company name
            
        Returns:
            str: Company research or empty string if not available
        """
        try:
            # Skip empty company names
            if not company or company.strip() == "":
                logging.warning("Empty company name detected, skipping research generation")
                return "No company name provided"
                
            # Create research directory if it doesn't exist
            research_dir = os.path.join(self.base_dir, 'company_research')
            if not os.path.exists(research_dir):
                os.makedirs(research_dir)
                
            # Create safe filename
            company_filename = company.replace('/', '_').replace('\\', '_')
            research_file = f"{research_dir}/{company_filename}.txt"
            
            # Check if research exists
            if os.path.exists(research_file):
                with open(research_file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    if len(lines) > 3:
                        # Skip the header lines
                        return ''.join(lines[3:]).strip()
                    
            # Generate research if it doesn't exist
            company_research = generate_company_research(company)
            if company_research:
                # Save research to file
                with open(research_file, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(f"Company Research for {company}\n")
                    f.write(f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(company_research)
                
                return company_research
                
            return ""
        except Exception as e:
            logging.error(f"Error getting company research: {str(e)}")
            return ""
                
    def save_to_csv(self, data: dict):
        """
        Save job application data to CSV file if it's not a duplicate.
        Also generates company research for new applications.
        Args:
            data (dict): Dictionary containing job application details with keys:
                        - title: Job title
                        - company: Company name
                        - status: Application status
                        - date: Application date
        """
        try:
            # Ensure all required fields are present
            required_fields = ['title', 'company', 'status', 'date']
            if not all(field in data for field in required_fields):
                missing_fields = [field for field in required_fields if field not in data]
                logging.error(f"Missing required fields: {missing_fields}")
                return False
            
            # Validate company name is not empty
            if not data['company'] or data['company'].strip() == "":
                logging.error("Empty company name detected, cannot save application")
                print("Cannot save application with empty company name")
                return False
                
            # Check for duplicates before saving
            if self._is_duplicate(data):
                logging.info(f"Skipped duplicate application: {data}")
                print(f"Skipped saving duplicate application: {data['title']} at {data['company']}")
                return True  # Return success even though we're skipping - this isn't an error
            
            # Generate company research for new applications
            company_research = self._get_company_research(data['company'])
            if company_research:
                print(f"\nCompany Research for {data['company']}:")
                print(f"{company_research}\n")
                
                # Add research to data
                data['research'] = company_research
            else:
                data['research'] = ""  # No research available
            
            # Handle encoding safely - instead of filtering characters, use proper encoding
            safe_data = {}
            for key, value in data.items():
                if isinstance(value, str):
                    # Keep all characters but replace problematic ones with their closest ASCII equivalent
                    safe_data[key] = value
                else:
                    safe_data[key] = value
                
            # Append data to CSV file with UTF-8 encoding and error handling
            with open(self.csv_file, 'a', newline='', encoding='utf-8', errors='replace') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'company', 'status', 'date', 'research'])
                writer.writerow(safe_data)
                
            logging.info(f"Saved job application: {data}")
            return True
        except Exception as e:
            logging.error(f"Error saving to CSV: {str(e)}")
            return False
            
    def get_all_applications(self):
        """Retrieve all job applications from the CSV file"""
        try:
            applications = []
            
            # Use proper encoding and error handling
            with open(self.csv_file, 'r', newline='', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    applications.append(row)
            return applications
        except Exception as e:
            logging.error(f"Error reading applications: {str(e)}")
            return []
    
    def remove_duplicates(self):
        """
        Remove duplicate job applications from the CSV file.
        This is useful for cleaning up the CSV file after multiple runs.
        """
        try:
            # Read all applications
            applications = self.get_all_applications()
            if not applications:
                logging.info("No applications found, nothing to deduplicate")
                return True
                
            # Track unique applications using title+company as key
            unique_apps = {}
            invalid_apps = []
            
            for app in applications:
                # Skip entries with empty company names
                if not app.get('company') or app.get('company', '').strip() == "":
                    logging.warning(f"Found entry with empty company name: {app.get('title', 'No title')}")
                    invalid_apps.append(app)
                    continue
                    
                key = (app['title'].lower(), app['company'].lower())
                # Keep the most recent entry if there are duplicates
                unique_apps[key] = app
                
            # Rewrite the CSV file with only unique applications
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'company', 'status', 'date', 'research'])
                writer.writeheader()
                for app in unique_apps.values():
                    # Ensure all required fields are present
                    if 'research' not in app:
                        # Get or generate research for this company
                        app['research'] = self._get_company_research(app['company'])
                    writer.writerow(app)
                    
            if invalid_apps:
                logging.info(f"Removed {len(invalid_apps)} entries with empty company names")
                print(f"Removed {len(invalid_apps)} entries with empty company names")
                
            logging.info(f"Deduplication complete. Reduced from {len(applications)} to {len(unique_apps)} applications")
            print(f"Deduplication complete. Reduced from {len(applications)} to {len(unique_apps)} applications")
            return True
        except Exception as e:
            logging.error(f"Error removing duplicates: {str(e)}")
            return False

def send_summary_email(summary):
    """
    Send an email summary of job applications with the CSV file attached.
    Args:
        summary (str): The summary text to send
    """
    try:
        # Get email configuration from .env
        sender_email = os.getenv('EMAIL_ADDRESS')
        sender_password = os.getenv('EMAIL_PASSWORD')
        recipient_email = sender_email  # Default to sending to self
        
        # Check if we have a specific recipient defined
        if os.getenv('EMAIL_RECIPIENT'):
            recipient_email = os.getenv('EMAIL_RECIPIENT')
        
        if not all([sender_email, sender_password]):
            logging.error("Email credentials not properly configured")
            return False
            
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"LinkedIn Job Application Tracker - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Add the summary to the email body
        msg.attach(MIMEText(summary, 'plain', 'utf-8'))
        
        # Attach the CSV file
        csv_file_path = 'job_applications.csv'
        if os.path.exists(csv_file_path):
            with open(csv_file_path, 'rb') as file:
                attachment = MIMEText(file.read().decode('utf-8', errors='replace'), 'csv', 'utf-8')
                attachment.add_header('Content-Disposition', 'attachment', filename='job_applications.csv')
                msg.attach(attachment)
            logging.info("Attached job applications CSV file to email")
            print("Attached job applications CSV file to email")
        else:
            logging.warning("Could not find job_applications.csv file to attach")
            print("Could not find job_applications.csv file to attach")
        
        # Connect to SMTP server and send email
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        logging.info("Summary email sent successfully")
        return True
    except Exception as e:
        logging.error(f"Error sending summary email: {str(e)}")
        return False

def log_job_summary(successful_applications):
    """
    Log job application summary to a file.
    Args:
        successful_applications (list): List of dictionaries containing job application details
    """
    try:
        # Ensure logs directory exists
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare log entry
        log_entry = f"\n{'='*80}\n"
        log_entry += f"Job Application Summary - {timestamp}\n"
        log_entry += f"{'='*80}\n\n"
        
        if successful_applications:
            log_entry += f"Found {len(successful_applications)} new job applications:\n\n"
            for i, app in enumerate(successful_applications, 1):
                log_entry += f"Application {i}:\n"
                log_entry += f"  Position: {app['title']}\n"
                log_entry += f"  Company: {app['company']}\n"
                log_entry += f"  Status: {app['status']}\n"
                log_entry += f"  Date: {app['date']}\n"
                log_entry += "-" * 50 + "\n"
        else:
            log_entry += "No new job applications were processed.\n"
            
        # Append to log file with proper encoding and error handling
        summary_log_path = os.path.join(log_dir, 'job_summary_log.txt')
        with open(summary_log_path, 'a', encoding='utf-8', errors='replace') as f:
            f.write(log_entry)
            
        logging.info("Job summary logged successfully")
        return True
    except Exception as e:
        logging.error(f"Error logging job summary: {str(e)}")
        return False

def generate_company_research(company_name):
    """
    Generate brief company research using OpenAI.
    Args:
        company_name (str): The name of the company to research
    Returns:
        str: Brief company research or None if generation fails
    """
    try:
        # Set OpenAI API key
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Prepare the prompt for company research
        prompt = f"""
        Provide a brief, factual summary of {company_name} as a company. Include:
        - Core business/industry
        - Company size and founded date (if known)
        - Key products or services
        - Notable company culture aspects
        
        Keep it under 150 words. Be concise and factual.
        """
        
        # Call OpenAI API with older version syntax
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise company research for job applicants."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        # Extract the response
        research = response.choices[0].message['content'].strip()
        logging.info(f"Successfully generated research for {company_name}")
        return research
        
    except Exception as e:
        logging.error(f"Error generating company research: {str(e)}")
        return None

def generate_research_for_all_companies():
    """
    Generate company research for all companies in the CSV file that don't have research yet.
    """
    try:
        # Create research directory if it doesn't exist
        research_dir = 'company_research'
        if not os.path.exists(research_dir):
            os.makedirs(research_dir)
            
        # Initialize tracker and get all applications
        tracker = JobApplicationTracker()
        applications = tracker.get_all_applications()
        
        if not applications:
            print("No applications found in CSV file.")
            return
            
        # Get unique companies
        companies = set(app['company'] for app in applications)
        print(f"Found {len(companies)} unique companies in your applications.")
        
        # Generate research for each company that doesn't have research yet
        for company in companies:
            # Create safe filename
            company_filename = company.replace('/', '_').replace('\\', '_')
            research_file = f"{research_dir}/{company_filename}.txt"
            
            # Skip if research already exists
            if os.path.exists(research_file):
                print(f"Research for {company} already exists.")
                continue
                
            print(f"Generating research for {company}...")
            company_research = generate_company_research(company)
            
            if company_research:
                # Save research to file
                with open(research_file, 'w', encoding='utf-8') as f:
                    f.write(f"Company Research for {company}\n")
                    f.write(f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(company_research)
                    
                print(f"✓ Research for {company} saved.")
            else:
                print(f"✗ Failed to generate research for {company}.")
                
        print("Company research generation completed.")
    except Exception as e:
        print(f"Error generating research for all companies: {str(e)}")
        logging.error(f"Error generating research for all companies: {str(e)}")

def run_agent():
    """
    Main function that orchestrates the job application tracking process:
    1. Fetches LinkedIn emails
    2. Extracts job information using GPT
    3. Saves data to CSV
    4. Generates company research
    5. Sends summary email
    6. Logs summary to file
    """
    try:
        print("Starting job application tracking process...")
        
        # Initialize tracker
        tracker = JobApplicationTracker()
        
        # Remove duplicates from existing applications
        print("Running deduplication on existing job applications...")
        tracker.remove_duplicates()
        
        # Generate research for all companies
        print("Generating research for all companies...")
        generate_research_for_all_companies()
        
        # Fetch LinkedIn emails
        print("Fetching LinkedIn emails...")
        emails = fetch_linkedin_emails()
        
        if not emails:
            print("No new LinkedIn emails found.")
            print("No email will be sent as there are no updates.")
            log_job_summary([])
            return
            
        print(f"Found {len(emails)} new LinkedIn emails.")
        
        # Track successful applications for summary
        successful_applications = []
        
        # Get today's date in a consistent format for comparison
        today_date = datetime.now().strftime('%Y-%m-%d')
        today_year = datetime.now().strftime('%Y')
        today_month_num = datetime.now().strftime('%m')
        today_day_num = datetime.now().strftime('%d')
        
        # Also get today's date in text format like "April 15, 2025"
        today_text_date = datetime.now().strftime('%B %d, %Y')
        
        # Process each email
        for i, email in enumerate(emails, 1):
            print(f"\nProcessing email {i}/{len(emails)}")
            print(f"Subject: {email['subject']}")
            
            # Extract job info using GPT
            print("Extracting job information...")
            job_info = extract_job_info(email['body'])
            
            if not job_info:
                print("Failed to extract job information from email.")
                continue
                
            # Save to CSV
            print("Saving job information...")
            if tracker.save_to_csv(job_info):
                print(f"Successfully saved job application:")
                print(f"  Title: {job_info['title']}")
                print(f"  Company: {job_info['company']}")
                print(f"  Status: {job_info['status']}")
                print(f"  Date: {job_info['date']}")
                successful_applications.append(job_info)
            else:
                print("Failed to save job information to CSV.")
        
        # Send summary email only if there are new applications
        if successful_applications:
            summary = f"Job Application Updates ({datetime.now().strftime('%Y-%m-%d')}):\n\n"
            
            # Get all applications from the CSV
            all_applications = tracker.get_all_applications()
            
            # Helper function to check if date is today
            def is_today(date_str):
                if not date_str or date_str.lower() in ["not provided", "not specified", "not available", "n/a"]:
                    return False
                
                # Try to standardize the date format for comparison
                date_str = date_str.strip()
                
                # Attempt to parse date string to datetime object for most accurate comparison
                try:
                    # Common date formats to check
                    date_formats = [
                        '%Y-%m-%d',          # 2025-04-15
                        '%B %d, %Y',         # April 15, 2025
                        '%b %d, %Y',         # Apr 15, 2025
                        '%d %B %Y',          # 15 April 2025
                        '%d %b %Y',          # 15 Apr 2025
                        '%m/%d/%Y',          # 04/15/2025
                        '%d/%m/%Y',          # 15/04/2025
                        '%Y/%m/%d',          # 2025/04/15
                    ]
                    
                    # Try each format until one works
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            # Compare year, month, and day components
                            if (parsed_date.year == datetime.now().year and 
                                parsed_date.month == datetime.now().month and 
                                parsed_date.day == datetime.now().day):
                                return True
                            break  # If we successfully parsed but dates don't match
                        except ValueError:
                            continue
                except Exception:
                    # If parsing fails, fall back to string-based checks
                    pass
                
                # String-based checks as fallbacks
                # Check exact match with today's date in different formats
                if today_date in date_str or today_text_date in date_str:
                    return True
                
                # Extract month and day from text format (handles cases like "April 15")
                month_day = datetime.now().strftime('%B %d')
                if month_day in date_str and today_year in date_str:
                    return True
                
                # Check for alternative formats that include today's components
                if (today_year in date_str and 
                    (today_month_num in date_str or datetime.now().strftime('%B') in date_str) and 
                    today_day_num in date_str):
                    return True
                
                return False
            
            # Filter applications that were submitted today from all applications
            todays_applications = [app for app in all_applications if is_today(app['date'])]
            
            if todays_applications:
                summary += f"Found {len(todays_applications)} job application(s) for today ({today_text_date}):\n\n"
                
                for app in todays_applications:
                    summary += f"Position: {app['title']}\n"
                    summary += f"Company: {app['company']}\n"
                    summary += f"Status: {app['status']}\n"
                    summary += f"Date: {app['date']}\n"
                    
                    # Add company research if available
                    if app.get('research'):
                        summary += f"\nCompany Research:\n{app['research']}\n"
                    else:
                        # Try to get research from file
                        research_file = f"company_research/{app['company'].replace('/', '_').replace('\\', '_')}.txt"
                        if os.path.exists(research_file):
                            with open(research_file, 'r', encoding='utf-8', errors='replace') as f:
                                lines = f.readlines()
                                if len(lines) > 3:  # Ensure we have content beyond headers
                                    research_content = ''.join(lines[3:])  # Skip the header lines
                                    summary += f"\nCompany Research:\n{research_content}\n"
                    
                    summary += "-" * 50 + "\n"
            else:
                summary += "No new applications were found today.\n"
                summary += "Applications in the report may be from previous days.\n\n"
                
                # Only include the most recent application if no applications are from today
                if successful_applications:
                    latest_app = successful_applications[-1]
                    summary += f"Most recent application:\n\n"
                    summary += f"Position: {latest_app['title']}\n"
                    summary += f"Company: {latest_app['company']}\n"
                    summary += f"Status: {latest_app['status']}\n"
                    summary += f"Date: {latest_app['date']}\n"
                    
                    # Add company research for the most recent application
                    if latest_app.get('research'):
                        summary += f"\nCompany Research:\n{latest_app['research']}\n"
                    else:
                        research_file = f"company_research/{latest_app['company'].replace('/', '_').replace('\\', '_')}.txt"
                        if os.path.exists(research_file):
                            with open(research_file, 'r', encoding='utf-8', errors='replace') as f:
                                lines = f.readlines()
                                if len(lines) > 3:  # Ensure we have content beyond headers
                                    research_content = ''.join(lines[3:])  # Skip the header lines
                                    summary += f"\nCompany Research:\n{research_content}\n"
                
                summary += "-" * 50 + "\n"
                
            # Add statistics at the end
            summary += f"\nTotal Applications: {len(all_applications)}\n"
            
            # Count by status
            status_counts = {}
            for app in all_applications:
                status = app['status']
                status_counts[status] = status_counts.get(status, 0) + 1
                
            # Add status breakdown
            summary += "\nApplication Status Breakdown:\n"
            for status, count in status_counts.items():
                summary += f"- {status}: {count}\n"
                
            # Add note about full list in CSV
            summary += "\nThe full list of applications is available in the attached CSV file.\n"
            
            print("\nSending summary email with new applications...")
            send_summary_email(summary)
            
            # Log summary to file
            print("Logging summary to file...")
            log_job_summary(successful_applications)
        else:
            print("No new job applications were successfully processed today.")
            print("No email will be sent as there are no updates.")
        
        print("Job application tracking process completed.")
        
    except Exception as e:
        print(f"Error in run_agent: {str(e)}")
        logging.error(f"Error in run_agent: {str(e)}")

def format_email_summary(today_applications):
    if not today_applications:
        return "No new job applications tracked today."
    
    summary = f"<h2>Job Applications Summary for {datetime.now().strftime('%B %d, %Y')}</h2>"
    summary += "<div style='font-family: Arial, sans-serif; padding: 15px;'>"
    summary += "<table style='width: 100%; border-collapse: collapse; margin-bottom: 20px;'>"
    summary += "<tr style='background-color: #f2f2f2;'>"
    summary += "<th style='padding: 10px; text-align: left; border: 1px solid #ddd;'>Job Title</th>"
    summary += "<th style='padding: 10px; text-align: left; border: 1px solid #ddd;'>Company</th>"
    summary += "<th style='padding: 10px; text-align: left; border: 1px solid #ddd;'>Status</th>"
    summary += "<th style='padding: 10px; text-align: left; border: 1px solid #ddd;'>Application Date</th>"
    summary += "</tr>"
    
    for app in today_applications:
        summary += f"<tr style='border: 1px solid #ddd;'>"
        summary += f"<td style='padding: 10px; border: 1px solid #ddd;'>{app['job_title']}</td>"
        summary += f"<td style='padding: 10px; border: 1px solid #ddd;'>{app['company']}</td>"
        summary += f"<td style='padding: 10px; border: 1px solid #ddd;'>{app['status']}</td>"
        summary += f"<td style='padding: 10px; border: 1px solid #ddd;'>{app['date']}</td>"
        summary += "</tr>"
    summary += "</table>"
    
    # Add statistics section
    total_apps = len(today_applications)
    companies = set(app['company'] for app in today_applications)
    
    summary += f"<div style='background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>"
    summary += f"<h3>Daily Statistics</h3>"
    summary += f"<p>Total applications submitted today: <strong>{total_apps}</strong></p>"
    summary += f"<p>Companies applied to: <strong>{len(companies)}</strong></p>"
    summary += "</div>"
    
    # Add company research highlights if available
    summary += "<h3>Company Research Highlights</h3>"
    summary += "<div style='margin-bottom: 20px;'>"
    
    for app in today_applications:
        if app.get('company_research') and len(app.get('company_research', '').strip()) > 10:
            summary += f"<div style='background-color: #f0f7ff; padding: 15px; border-radius: 5px; margin-bottom: 10px;'>"
            summary += f"<h4>{app['company']}</h4>"
            summary += f"<p>{app['company_research'].replace('\n', '<br>')}</p>"
            summary += "</div>"
    
    summary += "</div>"
    
    # Add motivational message
    summary += "<div style='padding: 15px; border-left: 4px solid #4CAF50; margin-top: 20px;'>"
    summary += "<p><i>Consistency is key in the job search process. Keep up the good work!</i></p>"
    summary += "</div>"
    
    summary += "</div>"
    return summary

if __name__ == "__main__":
    # Run the job application check once
    print("Running job application check...")
    run_agent() 