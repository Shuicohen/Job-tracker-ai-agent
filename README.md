# LinkedIn Job Application Tracker

A Python application that tracks LinkedIn job applications, generates company research using OpenAI, and sends daily email summaries with a complete CSV file of all applications.

## Features

- Fetches LinkedIn job applications data
- Generates company research using OpenAI
- Sends email summaries of new job applications
- Maintains a complete CSV file of all applications
- Deduplicates applications to avoid repetition
- Can be scheduled to run daily

## Requirements

- Python 3.7+
- OpenAI API key
- Gmail account (for sending emails)

## Installation

1. Clone this repository:
   ```
   git clone [repository-url]
   cd linkedin-job-email-tracker
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   EMAIL_USER=your_gmail_address
   EMAIL_PASSWORD=your_app_password
   EMAIL_RECIPIENT=recipient_email_address
   ```
   Note: For Gmail, you'll need to use an App Password. See [Google's documentation](https://support.google.com/accounts/answer/185833) for details.

## Usage

### Running Manually

To run the application once:

```
python main.py
```

### Running on a Schedule

To schedule the application to run daily at 9:00 AM:

1. Install the schedule package if not already installed:
   ```
   pip install schedule
   ```

2. Run the scheduler:
   ```
   python scheduler.py
   ```
   
3. The scheduler will:
   - Run the application immediately upon starting
   - Schedule it to run daily at 9:00 AM
   - Create logs in the `logs` directory

To run the scheduler as a background service, consider using:
- Windows: Task Scheduler
- Linux: systemd or cron
- macOS: launchd

## How It Works

1. The application fetches your LinkedIn job applications data
2. For each company, it generates research using OpenAI's API
3. It maintains a CSV file with all applications and company research
4. When run daily, it sends an email summarizing only the new applications found since the last run
5. Each email includes the complete CSV file as an attachment

## Troubleshooting

- Check the log files in the `logs` directory for error messages
- Ensure your OpenAI API key and email credentials are correct
- Make sure your Gmail account is set up to allow less secure apps or use an App Password

## License

[License information] 