# Deploying to Render

This guide explains how to deploy your LinkedIn Job Application Tracker to Render for continuous operation.

## Prerequisites

1. A [Render account](https://render.com/)
2. Your code pushed to a GitHub or GitLab repository

## Deployment Steps

### 1. Create a New Web Service on Render

1. Log in to your Render account
2. Click on "New" in the top right and select "Web Service"
3. Connect your GitHub/GitLab repository
4. Select the repository containing your LinkedIn Job Application Tracker

### 2. Configure the Web Service

Use the following settings:

- **Name**: linkedin-job-tracker (or your preferred name)
- **Environment**: Python
- **Region**: Choose the region closest to you
- **Branch**: main (or your default branch)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python server.py`

### 3. Add Environment Variables

Add the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key
- `EMAIL_ADDRESS`: Your Gmail address
- `EMAIL_PASSWORD`: Your app password for Gmail
- `EMAIL_RECIPIENT`: Email address to receive summaries (optional)
- `SMTP_SERVER`: smtp.gmail.com
- `SMTP_PORT`: 587

### 4. Add Persistent Disk

1. Scroll down to "Disks"
2. Click "Add Disk"
3. Set the following:
   - **Name**: data-storage
   - **Mount Path**: /data
   - **Size**: 1 GB

### 5. Deploy

Click "Create Web Service" to deploy your application.

## Post-Deployment

1. After deployment, your service will be available at a Render-provided URL
2. The application will run continuously
3. The job tracker will execute daily at 9:00 AM
4. All data will be stored on the persistent disk

## Troubleshooting

If your deployment encounters issues:

1. Check the Render logs for error messages
2. Verify that all environment variables are correctly set
3. Ensure your Gmail account is properly configured for app access
4. Check that the OpenAI API key is valid 