"""
Data services for managing job application data
"""
import os
import csv
from datetime import datetime
from app.config.settings import CSV_FILE, RESEARCH_DIR, logger
from app.services.ai_service import generate_company_research

class JobApplicationTracker:
    def __init__(self):
        self.csv_file = CSV_FILE
        self._ensure_files_exist()
        
    def _ensure_files_exist(self):
        """Ensure required files and directories exist"""
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
                    logger.info(f"Duplicate application found: {data['title']} at {data['company']}")
                    print(f"Duplicate application found: {data['title']} at {data['company']}")
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
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
                logger.warning("Empty company name detected, skipping research generation")
                return "No company name provided"
                
            # Create safe filename
            company_filename = company.replace('/', '_')
            company_filename = company_filename.replace('\\', '_')
            research_file = f"{RESEARCH_DIR}/{company_filename}.txt"
            
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
            logger.error(f"Error getting company research: {str(e)}")
            return ""
                
    def save_to_csv(self, data: dict):
        """
        Save job application data to CSV file if it's not a duplicate.
        Also generates company research for new applications.
        
        Args:
            data (dict): Dictionary containing job application details
                        - title: Job title
                        - company: Company name
                        - status: Application status
                        - date: Application date
                        
        Returns:
            bool: Success status
        """
        try:
            # Ensure all required fields are present
            required_fields = ['title', 'company', 'status', 'date']
            if not all(field in data for field in required_fields):
                missing_fields = [field for field in required_fields if field not in data]
                logger.error(f"Missing required fields: {missing_fields}")
                return False
            
            # Validate company name is not empty
            if not data['company'] or data['company'].strip() == "":
                logger.error("Empty company name detected, cannot save application")
                print("Cannot save application with empty company name")
                return False
                
            # Check for duplicates before saving
            if self._is_duplicate(data):
                logger.info(f"Skipped duplicate application: {data}")
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
                    # Keep all characters but handle encoding properly
                    safe_data[key] = value
                else:
                    safe_data[key] = value
                
            # Append data to CSV file with UTF-8 encoding and error handling
            with open(self.csv_file, 'a', newline='', encoding='utf-8', errors='replace') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'company', 'status', 'date', 'research'])
                writer.writerow(safe_data)
                
            logger.info(f"Saved job application: {data}")
            return True
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
            return False
            
    def get_all_applications(self):
        """
        Retrieve all job applications from the CSV file
        
        Returns:
            list: List of dictionaries containing job application details
        """
        try:
            applications = []
            
            # Use proper encoding and error handling
            with open(self.csv_file, 'r', newline='', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    applications.append(row)
            return applications
        except Exception as e:
            logger.error(f"Error reading applications: {str(e)}")
            return []
    
    def remove_duplicates(self):
        """
        Remove duplicate job applications from the CSV file.
        This is useful for cleaning up the CSV file after multiple runs.
        
        Returns:
            bool: Success status
        """
        try:
            # Read all applications
            applications = self.get_all_applications()
            if not applications:
                logger.info("No applications found, nothing to deduplicate")
                return True
                
            # Track unique applications using title+company as key
            unique_apps = {}
            invalid_apps = []
            
            for app in applications:
                # Skip entries with empty company names
                if not app.get('company') or app.get('company', '').strip() == "":
                    logger.warning(f"Found entry with empty company name: {app.get('title', 'No title')}")
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
                logger.info(f"Removed {len(invalid_apps)} entries with empty company names")
                print(f"Removed {len(invalid_apps)} entries with empty company names")
                
            logger.info(f"Deduplication complete. Reduced from {len(applications)} to {len(unique_apps)} applications")
            print(f"Deduplication complete. Reduced from {len(applications)} to {len(unique_apps)} applications")
            return True
        except Exception as e:
            logger.error(f"Error removing duplicates: {str(e)}")
            return False

def generate_research_for_all_companies():
    """
    Generate company research for all companies in the CSV file that don't have research yet.
    
    Returns:
        int: Number of companies for which research was generated
    """
    try:
        # Initialize tracker and get all applications
        tracker = JobApplicationTracker()
        applications = tracker.get_all_applications()
        
        if not applications:
            print("No applications found in CSV file.")
            return 0
            
        # Get unique companies
        companies = set(app['company'] for app in applications)
        print(f"Found {len(companies)} unique companies in your applications.")
        
        research_generated = 0
        
        # Generate research for each company that doesn't have research yet
        for company in companies:
            # Skip if company name is empty
            if not company or company.strip() == "":
                continue
                
            # Create safe filename
            company_filename = company.replace('/', '_')
            company_filename = company_filename.replace('\\', '_')
            research_file = f"{RESEARCH_DIR}/{company_filename}.txt"
            
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
                research_generated += 1
            else:
                print(f"✗ Failed to generate research for {company}.")
                
        print("Company research generation completed.")
        return research_generated
    except Exception as e:
        print(f"Error generating research for all companies: {str(e)}")
        logger.error(f"Error generating research for all companies: {str(e)}")
        return 0 