"""
AI services using OpenAI API for job information extraction and company research
"""
import json
import openai
import time
from app.config.settings import OPENAI_API_KEY, OPENAI_MODEL, logger

def extract_job_info(email_body):
    """
    Extract job information from email body using OpenAI GPT.
    Returns a dictionary with job details or None if extraction fails.
    
    Args:
        email_body (str): The email body text to analyze
        
    Returns:
        dict: Dictionary containing job details or None if extraction fails
    """
    try:
        # Set OpenAI API key
        openai.api_key = OPENAI_API_KEY
        
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
        
        # Call OpenAI API using the client format
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts job application details from emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1  # Low temperature for more consistent output
        )
        
        # Extract and parse the JSON response
        json_str = response.choices[0].message.content.strip()
        
        # Add error handling for possible JSON issues
        # Remove any markdown code blocks if present
        if json_str.startswith("```json"):
            json_str = json_str.replace("```json", "").replace("```", "").strip()
        elif json_str.startswith("```"):
            json_str = json_str.replace("```", "").strip()
            
        job_info = json.loads(json_str)
        
        logger.info(f"Successfully extracted job info: {job_info}")
        return job_info
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        logger.error(f"JSON string was: {json_str if 'json_str' in locals() else 'Not available'}")
        return None
    except Exception as e:
        logger.error(f"Error extracting job info: {str(e)}")
        return None

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
        openai.api_key = OPENAI_API_KEY
        
        # Prepare the prompt for company research
        prompt = f"""
        Provide a brief, factual summary of {company_name} as a company. Include:
        - Core business/industry
        - Company size and founded date (if known)
        - Key products or services
        - Notable company culture aspects
        
        Keep it under 150 words. Be concise and factual.
        """
        
        # Call OpenAI API with client syntax
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise company research for job applicants."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        # Extract the response
        research = response.choices[0].message.content.strip()
        logger.info(f"Successfully generated research for {company_name}")
        return research
        
    except Exception as e:
        logger.error(f"Error generating company research: {str(e)}")
        return None 