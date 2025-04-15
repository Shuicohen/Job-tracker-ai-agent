"""
Email sending functionality
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from app.config.settings import (
    EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_RECIPIENT, 
    SMTP_SERVER, SMTP_PORT, CSV_FILE, logger
)

def send_summary_email(summary):
    """
    Send an email summary of job applications with the CSV file attached.
    Args:
        summary (str): The summary text to send in HTML format
    """
    try:
        if not all([EMAIL_ADDRESS, EMAIL_PASSWORD]):
            logger.error("Email credentials not properly configured")
            return False
            
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_RECIPIENT or EMAIL_ADDRESS  # Default to sender if recipient not defined
        msg['Subject'] = f"LinkedIn Job Application Tracker - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Add the summary to the email body as HTML content
        msg.attach(MIMEText(summary, 'html', 'utf-8'))
        
        # Attach the CSV file
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'rb') as file:
                attachment = MIMEText(file.read().decode('utf-8', errors='replace'), 'csv', 'utf-8')
                attachment.add_header('Content-Disposition', 'attachment', filename='job_applications.csv')
                msg.attach(attachment)
            logger.info("Attached job applications CSV file to email")
            print("Attached job applications CSV file to email")
        else:
            logger.warning("Could not find job_applications.csv file to attach")
            print("Could not find job_applications.csv file to attach")
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            
        logger.info("Summary email sent successfully")
        return True
    except Exception as e:
        logger.error(f"Error sending summary email: {str(e)}")
        return False

def format_email_summary(today_applications):
    """
    Format email summary in HTML for better readability
    
    Args:
        today_applications (list): Today's applications to summarize
        
    Returns:
        str: Formatted HTML email content
    """
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
        summary += f"<td style='padding: 10px; border: 1px solid #ddd;'>{app['title']}</td>"
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
        if app.get('research') and len(app.get('research', '').strip()) > 10:
            summary += f"<div style='background-color: #f0f7ff; padding: 15px; border-radius: 5px; margin-bottom: 10px;'>"
            summary += f"<h4>{app['company']}</h4>"
            # Handle newline replacement without using backslash in f-string
            company_research = app['research']
            formatted_research = company_research.replace('\n', '<br>')
            summary += f"<p>{formatted_research}</p>"
            summary += "</div>"
    
    summary += "</div>"
    
    # Add motivational message
    summary += "<div style='padding: 15px; border-left: 4px solid #4CAF50; margin-top: 20px;'>"
    summary += "<p><i>Consistency is key in the job search process. Keep up the good work!</i></p>"
    summary += "</div>"
    
    summary += "</div>"
    return summary 