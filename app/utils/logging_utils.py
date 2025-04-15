"""
Logging utility functions
"""
import os
from datetime import datetime
from app.config.settings import LOG_DIR, logger

def log_job_summary(successful_applications):
    """
    Log job application summary to a file.
    Args:
        successful_applications (list): List of dictionaries containing job application details
    """
    try:
        # Ensure logs directory exists
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
            
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
        summary_log_path = os.path.join(LOG_DIR, 'job_summary_log.txt')
        with open(summary_log_path, 'a', encoding='utf-8', errors='replace') as f:
            f.write(log_entry)
            
        logger.info("Job summary logged successfully")
        return True
    except Exception as e:
        logger.error(f"Error logging job summary: {str(e)}")
        return False 