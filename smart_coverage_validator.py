import json
import os
from typing import Dict, List
from openai import OpenAI
from pathlib import Path
import logging
from datetime import datetime
from dotenv import load_dotenv
import time
import re

# Load environment variables from .env file
load_dotenv()

class SmartPreMedValidator:
    """
    Intelligent content validator using GPT-4 to assess medical school content coverage
    for pre-med student needs
    """
    
    def __init__(self, school_name: str, content_path: str):
        """Initialize validator with school name and path to content"""
        self.school_name = school_name
        self.content_path = Path(content_path)
        self.setup_logging()
        
        # Ensure OpenAI API key is set
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable must be set")
            
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Priority content patterns
        self.priority_patterns = {
            'admissions': [
                r'admissions?',
                r'requirements?',
                r'application',
                r'deadlines?',
                r'MCAT',
                r'GPA',
                r'prerequisites?'
            ],
            'financial': [
                r'financial aid',
                r'tuition',
                r'scholarships?',
                r'costs?',
                r'funding',
                r'loans?'
            ],
            'curriculum': [
                r'curriculum',
                r'courses?',
                r'program',
                r'clinical',
                r'rotations?',
                r'clerkships?'
            ],
            'student_life': [
                r'student life',
                r'housing',
                r'campus',
                r'activities',
                r'organizations?'
            ]
        }
        
        # Core information categories pre-med students need
        self.core_categories = [
            {
                "name": "Admissions Process & Requirements",
                "description": "Understanding the complete application process, requirements, and selection criteria",
                "key_aspects": [
                    "Application process steps and timeline",
                    "Academic requirements (courses, GPA)",
                    "Standardized test requirements",
                    "Selection criteria and evaluation process",
                    "Interview process",
                    "Unique admissions programs or pathways"
                ]
            },
            {
                "name": "Curriculum & Academic Experience",
                "description": "Details about the medical education program structure and learning experience",
                "key_aspects": [
                    "Curriculum overview and structure",
                    "Pre-clinical and clinical training",
                    "Learning methods and resources",
                    "Evaluation and grading systems",
                    "Academic support services",
                    "Unique educational programs or tracks"
                ]
            },
            {
                "name": "Research & Scholarly Opportunities",
                "description": "Available research and academic enrichment opportunities",
                "key_aspects": [
                    "Research programs and opportunities",
                    "Mentorship availability",
                    "Funding for research",
                    "Publication and presentation opportunities",
                    "Special research tracks or programs",
                    "Research facilities and resources"
                ]
            },
            {
                "name": "Clinical Experience & Training",
                "description": "Clinical exposure and hands-on training opportunities",
                "key_aspects": [
                    "Clinical rotation structure",
                    "Hospital and clinical sites",
                    "Patient interaction opportunities",
                    "Specialty exposure",
                    "Early clinical exposure programs",
                    "Clinical skills development"
                ]
            },
            {
                "name": "Financial Information",
                "description": "Complete understanding of costs and financial support",
                "key_aspects": [
                    "Tuition and fees",
                    "Financial aid availability",
                    "Scholarships and grants",
                    "Loan programs",
                    "Cost of living considerations",
                    "Financial planning resources"
                ]
            },
            {
                "name": "Student Life & Support",
                "description": "Student experience, wellness, and support systems",
                "key_aspects": [
                    "Student wellness programs",
                    "Housing and living arrangements",
                    "Student organizations and activities",
                    "Mentoring and advising",
                    "Career counseling",
                    "Campus facilities and resources"
                ]
            },
            {
                "name": "Special Programs & Opportunities",
                "description": "Unique programs, tracks, and educational opportunities",
                "key_aspects": [
                    "Dual degree programs",
                    "Special admission programs",
                    "Research tracks",
                    "Global health opportunities",
                    "Community service programs",
                    "Leadership development"
                ]
            }
        ]
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Create handlers
        file_handler = logging.FileHandler(
            log_dir / f"validation_{self.school_name}_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        console_handler = logging.StreamHandler()
        
        # Create formatters and add it to handlers
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(log_format)
        console_handler.setFormatter(log_format)
        
        # Add handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def filter_priority_content(self, content: Dict) -> Dict:
        """Filter content based on priority patterns"""
        filtered_content = {}
        
        for url, page_data in content.items():
            text = ' '.join(page_data.get('text_chunks', []))
            
            # Check each priority category
            for category, patterns in self.priority_patterns.items():
                if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                    if category not in filtered_content:
                        filtered_content[category] = {}
                    filtered_content[category][url] = page_data
        
        return filtered_content
    
    def analyze_category_coverage(self, content: Dict, category: Dict) -> Dict:
        """
        Use GPT-4 to analyze coverage of a specific category
        """
        # Get relevant content for this category
        filtered_content = self.filter_priority_content(content)
        relevant_category = None
        
        if "admissions" in category["name"].lower():
            relevant_category = "admissions"
        elif "curriculum" in category["name"].lower():
            relevant_category = "curriculum"
        elif "financial" in category["name"].lower():
            relevant_category = "financial"
        elif "student life" in category["name"].lower():
            relevant_category = "student_life"
        
        # Prepare content for analysis
        content_text = ""
        if relevant_category and relevant_category in filtered_content:
            for url, page_data in filtered_content[relevant_category].items():
                content_text += f"\nPage: {url}\n"
                content_text += f"Title: {page_data['title']}\n"
                content_text += "\n".join(page_data.get('text_chunks', []))
        else:
            # Fallback to using all content if no specific category match
            sample_content = dict(list(content.items())[:5])  # Take first 5 pages
            for url, page_data in sample_content.items():
                content_text += f"\nPage: {url}\n"
                content_text += f"Title: {page_data['title']}\n"
                content_text += "\n".join(page_data.get('text_chunks', []))
        
        # Truncate content to fit token limits while keeping complete sentences
        content_text = self.smart_truncate(content_text, 8000)
        
        # Construct prompt for GPT-4
        prompt = f"""
        You are an expert in medical education and pre-medical advising. Analyze the following content from {self.school_name}'s website regarding {category['name']}.

        Category Description: {category['description']}
        Key Aspects to Look For:
        {chr(10).join(f'- {aspect}' for aspect in category['key_aspects'])}

        Analyze the content for coverage of these aspects. Consider:
        1. Is each key aspect adequately covered?
        2. Is the information clear and detailed enough for pre-med students?
        3. Are there any significant gaps in coverage?
        4. Are there unique programs or opportunities that should be highlighted?
        5. What additional information would be valuable for pre-med students?

        Content to analyze:
        {content_text}

        Provide a structured analysis with:
        1. Coverage Assessment (0-100%)
        2. Strengths
        3. Gaps
        4. Recommendations
        """

        max_retries = 3
        retry_delay = 1  # Start with 1 second delay

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an expert medical education advisor analyzing website content coverage."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                
                analysis = response.choices[0].message.content
                
                self.logger.info(f"Completed analysis of {category['name']}")
                return {
                    "category": category['name'],
                    "analysis": analysis
                }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Error on attempt {attempt + 1}, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed after {max_retries} attempts: {e}")
                    return {
                        "category": category['name'],
                        "error": f"Error after {max_retries} attempts: {str(e)}"
                    }
    
    def smart_truncate(self, text: str, max_chars: int) -> str:
        """Truncate text at sentence boundary near max_chars"""
        if len(text) <= max_chars:
            return text
            
        # Find the last period before max_chars
        last_period = text[:max_chars].rfind('.')
        if last_period > 0:
            return text[:last_period + 1]
        
        # If no period found, truncate at max_chars
        return text[:max_chars]
    
    def validate_coverage(self) -> List[Dict]:
        """
        Validate coverage across all categories
        """
        content = self.load_content()
        results = []
        
        self.logger.info(f"Starting content validation for {self.school_name}")
        
        for category in self.core_categories:
            self.logger.info(f"Analyzing category: {category['name']}")
            result = self.analyze_category_coverage(content, category)
            results.append(result)
            
        self.logger.info("Validation complete")
        return results
    
    def load_content(self) -> Dict:
        """Load scraped content from JSON file"""
        try:
            with open(self.content_path) as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading content from {self.content_path}: {e}")
            raise
    
    def generate_report(self, results: List[Dict]) -> str:
        """
        Generate a comprehensive coverage report
        """
        report = f"""
        Content Coverage Analysis Report
        School: {self.school_name}
        Date: {datetime.now():%Y-%m-%d %H:%M:%S}
        
        Executive Summary
        ================
        """
        
        for result in results:
            report += f"\n\n{result['category']}\n{'=' * len(result['category'])}\n"
            if 'error' in result:
                report += f"Error during analysis: {result['error']}\n"
            else:
                report += result['analysis']
        
        report_path = Path("reports") / f"{self.school_name}_coverage_report_{datetime.now():%Y%m%d_%H%M%S}.txt"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        self.logger.info(f"Report generated: {report_path}")
        return report

def main():
    """Main function to run the validator"""
    validator = SmartPreMedValidator(
        school_name="Mount Sinai",
        content_path="scraped_content/mount_sinai/processed/mount_sinai_processed.json"
    )
    results = validator.validate_coverage()
    report = validator.generate_report(results)
    print("\nReport generated. Check the reports directory for the full analysis.")

if __name__ == "__main__":
    main()
