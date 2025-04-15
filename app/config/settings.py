"""
Configuration settings for the application.
Loads environment variables and provides settings for the application.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Determine base directory - use /data if on Render
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = '/data' if os.path.exists('/data') else BASE_DIR

# Determine log directory
LOG_DIR = os.path.join(DATA_DIR, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Research directory for company research files
RESEARCH_DIR = os.path.join(DATA_DIR, 'company_research')
if not os.path.exists(RESEARCH_DIR):
    os.makedirs(RESEARCH_DIR)

# CSV file path
CSV_FILE = os.path.join(DATA_DIR, 'job_applications.csv')

# Email Settings
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT', EMAIL_ADDRESS)  # Default to sender
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))

# IMAP settings for fetching emails
IMAP_SERVER = 'imap.gmail.com'

# OpenAI settings
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'applications.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Get logger instance
logger = logging.getLogger(__name__) 