"""
Main application module for the LinkedIn Job Application Tracker
"""
from datetime import datetime
from app.config.settings import logger
from app.email.email_parser import fetch_linkedin_emails
from app.email.email_sender import send_summary_email, format_email_summary
from app.services.ai_service import extract_job_info
from app.services.data_service import JobApplicationTracker, generate_research_for_all_companies
from app.utils.logging_utils import log_job_summary

def is_today(date_str):
    """
    Helper function to check if a date string represents today's date
    
    Args:
        date_str (str): Date string to check
        
    Returns:
        bool: True if date is today, False otherwise
    """
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
        
        # Get today's date in different formats for comparisons
        today_date = datetime.now().strftime('%Y-%m-%d')
        today_year = datetime.now().strftime('%Y')
        today_month_num = datetime.now().strftime('%m')
        today_day_num = datetime.now().strftime('%d')
        today_text_date = datetime.now().strftime('%B %d, %Y')
        
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
    today_date = datetime.now().strftime('%Y-%m-%d')
    today_text_date = datetime.now().strftime('%B %d, %Y')
    
    if today_date in date_str or today_text_date in date_str:
        return True
    
    # Extract month and day from text format (handles cases like "April 15")
    month_day = datetime.now().strftime('%B %d')
    today_year = datetime.now().strftime('%Y')
    
    if month_day in date_str and today_year in date_str:
        return True
    
    # Check for alternative formats that include today's components
    today_month_num = datetime.now().strftime('%m')
    today_day_num = datetime.now().strftime('%d')
    
    if (today_year in date_str and 
        (today_month_num in date_str or datetime.now().strftime('%B') in date_str) and 
        today_day_num in date_str):
        return True
    
    return False

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
            # Get all applications from the CSV
            all_applications = tracker.get_all_applications()
            
            # Filter applications that were submitted today
            todays_applications = [app for app in all_applications if is_today(app['date'])]
            
            if todays_applications:
                print(f"\nFound {len(todays_applications)} applications for today.")
            else:
                print("\nNo applications submitted today found in tracker.")
                
            # Create email summary
            print("\nCreating and sending email summary...")
            # Use either todays_applications or successful_applications, prioritizing today's
            applications_to_summarize = todays_applications if todays_applications else successful_applications
            email_summary = format_email_summary(applications_to_summarize)
            send_summary_email(email_summary)
            
            # Log summary to file
            print("Logging summary to file...")
            log_job_summary(successful_applications)
        else:
            print("No new job applications were successfully processed.")
            print("No email will be sent as there are no updates.")
        
        print("Job application tracking process completed.")
        
    except Exception as e:
        print(f"Error in run_agent: {str(e)}")
        logger.error(f"Error in run_agent: {str(e)}")

if __name__ == "__main__":
    run_agent() 