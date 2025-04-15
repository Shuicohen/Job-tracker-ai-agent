import schedule
import time
import os
import sys
import logging
from datetime import datetime

# Determine log directory (use /data if on Render)
log_dir = '/data/logs' if os.path.exists('/data') else 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'scheduler.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def run_job_tracker():
    """Run the job tracker application"""
    try:
        logging.info("Running scheduled job tracker...")
        
        # Ensure we're in the correct directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Run the main script
        os.system('python main.py')
        
        logging.info("Scheduled job completed successfully.")
    except Exception as e:
        logging.error(f"Error running scheduled job: {str(e)}")

def main():
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Schedule the job to run daily at 9:00 AM
    schedule.every().day.at("09:00").do(run_job_tracker)
    
    # Also run once immediately on start
    run_job_tracker()
    
    # For Render deployment - keep the process alive
    PORT = int(os.environ.get("PORT", 8080))
    
    logging.info("Scheduler started. Will run daily at 09:00 AM.")
    print("Scheduler started. Will run daily at 09:00 AM.")
    print(f"Service running on port {PORT}")
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logging.info("Scheduler stopped by user.")
        print("\nScheduler stopped. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main() 