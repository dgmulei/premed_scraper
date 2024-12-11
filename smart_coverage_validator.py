import json
import os
from typing import Dict, List, Tuple
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
    
    def __init__(self, school_name: str, web_content_path: str, pdf_content_path: str):
        """Initialize validator with school name and paths to content"""
        self.school_name = school_name
        self.web_content_path = Path(web_content_path)
        self.pdf_content_path = Path(pdf_content_path)
        self.setup_logging()
        
        # Ensure OpenAI API key is set
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable must be set")
            
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Enhanced category mapping with more specific terms
        self.category_map = {
            "Admissions Process & Requirements": {
                "must_include": ["admissions process", "application requirements", "how to apply"],
                "primary": ["admissions criteria", "application deadline", "prerequisites", "MCAT requirement"],
                "related": ["selection process", "interview", "eligibility", "application review"]
            },
            "Financial Information": {
                "must_include": ["tuition", "cost of attendance", "financial aid"],
                "primary": ["scholarship", "grant", "loan", "FAFSA"],
                "related": ["payment", "budget", "expense", "fee"]
            },
            "Curriculum & Academic Experience": {
                "must_include": ["curriculum", "medical education", "course requirements"],
                "primary": ["preclinical", "clinical training", "clerkship", "rotation"],
                "related": ["academic program", "learning objectives", "educational"]
            },
            "Research & Scholarly Opportunities": {
                "must_include": ["research opportunities", "scholarly activities", "research programs"],
                "primary": ["laboratory research", "clinical research", "research funding"],
                "related": ["publication", "presentation", "investigation"]
            },
            "Clinical Experience & Training": {
                "must_include": ["clinical training", "patient care", "clinical experience"],
                "primary": ["clinical rotation", "clerkship", "hospital", "patient interaction"],
                "related": ["clinical skills", "clinical sites", "specialty"]
            },
            "Student Life & Support": {
                "must_include": ["student life", "campus life", "student support"],
                "primary": ["housing", "student organization", "wellness program"],
                "related": ["mentoring", "counseling", "student services"]
            },
            "Special Programs & Opportunities": {
                "must_include": ["special programs", "dual degree", "combined program"],
                "primary": ["MD-PhD", "global health", "research track"],
                "related": ["leadership", "community service", "special opportunity"]
            }
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
    
    def extract_pdf_text(self, pdf_data: Dict) -> str:
        """Extract text from PDF data structure"""
        text_parts = []
        
        # Extract text from pages
        if isinstance(pdf_data.get('content', {}), dict):
            text_pages = pdf_data['content'].get('text', [])
            for page in text_pages:
                if isinstance(page, dict) and 'text' in page:
                    text_parts.append(page['text'])
        
        # Add metadata information
        metadata = pdf_data.get('metadata', {})
        if metadata:
            text_parts.extend([
                str(metadata.get('title', '')),
                str(metadata.get('type', '')),
                str(metadata.get('subtype', '')),
                str(metadata.get('description', ''))
            ])
        
        # Add extracted data
        extracted_data = pdf_data.get('content', {}).get('extracted_data', {})
        if extracted_data:
            for key, values in extracted_data.items():
                if values:
                    text_parts.append(f"{key}: {', '.join(str(v) for v in values)}")
        
        # Add table data if available
        tables = pdf_data.get('content', {}).get('tables', [])
        if tables:
            for page_tables in tables:
                if isinstance(page_tables, dict) and 'tables' in page_tables:
                    for table in page_tables['tables']:
                        for row in table:
                            if isinstance(row, list):
                                text_parts.append(' '.join(str(cell) for cell in row if cell))
        
        # Combine all text parts
        return '\n'.join(text_parts)
    
    def calculate_content_relevance(self, text: str, category_terms: Dict) -> Tuple[bool, float]:
        """Calculate content relevance score and validate must-include terms"""
        # Check for must-include terms
        must_include_found = False
        for term in category_terms['must_include']:
            if term.lower() in text.lower():
                must_include_found = True
                break
        
        # Calculate relevance score
        score = 0
        total_terms = 0
        
        # Primary terms are worth 2 points
        for term in category_terms['primary']:
            if re.search(rf'\b{term}\b', text, re.IGNORECASE):
                score += 2
            total_terms += 2
        
        # Related terms are worth 1 point
        for term in category_terms['related']:
            if re.search(rf'\b{term}\b', text, re.IGNORECASE):
                score += 1
            total_terms += 1
        
        # Calculate relevance score as percentage
        relevance_score = score / total_terms if total_terms > 0 else 0
        
        return must_include_found, relevance_score
    
    def filter_content_by_category(self, content: Dict, category: Dict, source_type: str = 'web') -> Dict:
        """Filter content based on category terms with relevance scoring"""
        filtered_content = {}
        category_terms = self.category_map.get(category["name"])
        
        if not category_terms:
            return filtered_content
        
        if source_type == 'web':
            for url, page_data in content.items():
                text = ' '.join(page_data.get('text_chunks', []))
                must_include, relevance = self.calculate_content_relevance(text, category_terms)
                
                if must_include and relevance > 0.2:  # Require at least 20% relevance
                    filtered_content[url] = {
                        **page_data,
                        'relevance_score': relevance
                    }
        
        elif source_type == 'pdf':
            for filename, pdf_data in content.items():
                full_text = self.extract_pdf_text(pdf_data)
                must_include, relevance = self.calculate_content_relevance(full_text, category_terms)
                
                if must_include and relevance > 0.2:  # Require at least 20% relevance
                    filtered_content[filename] = {
                        'metadata': pdf_data.get('metadata', {}),
                        'content': full_text,
                        'extracted_data': pdf_data.get('content', {}).get('extracted_data', {}),
                        'relevance_score': relevance
                    }
        
        # Sort content by relevance score
        return dict(sorted(
            filtered_content.items(),
            key=lambda x: x[1]['relevance_score'],
            reverse=True
        ))
    
    def analyze_category_coverage(self, web_content: Dict, pdf_content: Dict, category: Dict) -> Dict:
        """
        Use GPT-4 to analyze coverage of a specific category from both web and PDF sources
        """
        # Filter content by category
        filtered_web = self.filter_content_by_category(web_content, category, 'web')
        filtered_pdf = self.filter_content_by_category(pdf_content, category, 'pdf')
        
        # Log filtering results
        self.logger.info(f"Filtered web content for {category['name']}: {len(filtered_web)} items")
        self.logger.info(f"Filtered PDF content for {category['name']}: {len(filtered_pdf)} items")
        
        # Prepare content for analysis
        content_text = "=== Website Content ===\n"
        web_content_found = False
        
        # Take top 10 most relevant web pages
        for url, page_data in list(filtered_web.items())[:10]:
            content_text += f"\nPage: {url}\n"
            content_text += f"Title: {page_data.get('title', 'No title')}\n"
            content_text += f"Relevance Score: {page_data['relevance_score']:.2%}\n"
            content_text += "\n".join(page_data.get('text_chunks', []))
            web_content_found = True
        
        if not web_content_found:
            content_text += "\nNo relevant website content found.\n"
        
        content_text += "\n\n=== PDF Documents ===\n"
        pdf_content_found = False
        
        # Take top 10 most relevant PDFs
        for filename, pdf_data in list(filtered_pdf.items())[:10]:
            content_text += f"\nDocument: {filename}\n"
            content_text += f"Type: {pdf_data['metadata'].get('type', 'Unknown')}\n"
            content_text += f"Subtype: {pdf_data['metadata'].get('subtype', 'Unknown')}\n"
            content_text += f"Relevance Score: {pdf_data['relevance_score']:.2%}\n"
            content_text += f"Content:\n{pdf_data['content']}\n"
            
            # Include extracted data if available
            if pdf_data['extracted_data']:
                content_text += "\nExtracted Information:\n"
                for key, values in pdf_data['extracted_data'].items():
                    if values:
                        content_text += f"{key}: {', '.join(str(v) for v in values)}\n"
            pdf_content_found = True
        
        if not pdf_content_found:
            content_text += "\nNo relevant PDF documents found.\n"
        
        # Log content analysis
        self.logger.info(f"Analyzing content for category: {category['name']}")
        self.logger.info(f"Web content found: {web_content_found}")
        self.logger.info(f"PDF content found: {pdf_content_found}")
        
        # Truncate content to fit token limits while keeping complete sentences
        content_text = self.smart_truncate(content_text, 8000)
        
        # Construct prompt for GPT-4
        prompt = f"""
        You are an expert in medical education and pre-medical advising. Analyze the following content from {self.school_name}'s website and documents regarding {category['name']}.

        Category Description: {category['description']}
        Key Aspects to Look For:
        {chr(10).join(f'- {aspect}' for aspect in category['key_aspects'])}

        Analyze the content for coverage of these aspects. Consider:
        1. Is each key aspect adequately covered?
        2. Is the information clear and detailed enough for pre-med students?
        3. Are there any significant gaps in coverage?
        4. Are there unique programs or opportunities that should be highlighted?
        5. What additional information would be valuable for pre-med students?
        6. How well do the website and PDF documents complement each other?

        Content to analyze:
        {content_text}

        Provide a structured analysis with:
        1. Coverage Assessment (0-100% with breakdown by key aspect)
        2. Strengths (specific examples from both website and PDFs)
        3. Gaps (missing or inadequately covered information)
        4. Website vs PDF Coverage Comparison (how they complement each other)
        5. Recommendations (specific suggestions for improvement)
        """

        max_retries = 3
        retry_delay = 1  # Start with 1 second delay

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert medical education advisor analyzing website and document content coverage."},
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
    
    def load_content(self) -> tuple[Dict, Dict]:
        """Load web and PDF content"""
        try:
            # Load web content
            with open(self.web_content_path) as f:
                web_content = json.load(f)
            
            # Load PDF content
            with open(self.pdf_content_path) as f:
                pdf_content = json.load(f)
            
            # Log content loading
            self.logger.info(f"Loaded {len(web_content)} web pages")
            self.logger.info(f"Loaded {len(pdf_content)} PDF documents")
            
            return web_content, pdf_content
            
        except Exception as e:
            self.logger.error(f"Error loading content: {e}")
            raise
    
    def validate_coverage(self) -> List[Dict]:
        """
        Validate coverage across all categories using both web and PDF content
        """
        web_content, pdf_content = self.load_content()
        results = []
        
        self.logger.info(f"Starting content validation for {self.school_name}")
        self.logger.info(f"Analyzing {len(web_content)} web pages and {len(pdf_content)} PDF documents")
        
        for category in self.core_categories:
            self.logger.info(f"Analyzing category: {category['name']}")
            result = self.analyze_category_coverage(web_content, pdf_content, category)
            results.append(result)
            
        self.logger.info("Validation complete")
        return results
    
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
        This analysis includes both website content and PDF documents.
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
        web_content_path="scraped_content/processed/mount_sinai_processed.json",
        pdf_content_path="scraped_content/processed/mount_sinai_pdfs_processed.json"
    )
    results = validator.validate_coverage()
    report = validator.generate_report(results)
    print("\nReport generated. Check the reports directory for the full analysis.")

if __name__ == "__main__":
    main()
