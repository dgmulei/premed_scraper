import os
import re
import json
import time
import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from text_cleaner import clean_text

class ScraperConfig:
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or 'scraped_content'
        self.raw_dir = os.path.join(self.output_dir, 'raw')
        self.processed_dir = os.path.join(self.output_dir, 'processed')
        self.pdf_dir = os.path.join(self.output_dir, 'pdfs')  # New PDF directory
        
        # Create directories if they don't exist
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.pdf_dir, exist_ok=True)  # Create PDF directory
        
        # Set file paths
        self.raw_file = os.path.join(self.raw_dir, 'mount_sinai_raw.json')
        self.processed_file = os.path.join(self.processed_dir, 'mount_sinai_processed.json')

class MountSinaiScraper:
    def __init__(self, config=None):
        self.config = config or ScraperConfig()
        self.base_url = "https://icahn.mssm.edu"
        self.session = requests.Session()
        self.visited_urls = set()
        self.content = {}
        self.text_cleaner = clean_text
        self.downloaded_pdfs = set()  # Track downloaded PDFs
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
        # Updated paths to include both financial and admissions
        self.important_paths = [
            # Financial paths
            '/education/financial-aid',
            '/education/student-financial-services',
            '/education/enhanced-scholarship-initiative',
            '/education/financial-aid/application',
            '/education/financial-aid/md-need-based',
            '/education/financial-aid/css-profile',
            '/education/financial-aid/fafsa',
            '/education/financial-aid/loans',
            '/education/financial-aid/tuition',
            '/education/financial-aid/payment',
            '/education/financial-aid/scholarships',
            '/education/admissions/financial-aid',
            '/education/medical/financial-aid',
            # Admissions paths
            '/education/medical/admissions',
            '/education/medical/admissions/how-to-apply',
            '/education/medical/admissions/requirements',
            '/education/medical/admissions/selection-process',
            '/education/medical/admissions/interview',
            '/education/medical/admissions/timeline',
            '/education/medical/admissions/mcat',
            '/education/medical/admissions/prerequisites'
        ]
        
        # Content keywords for categorization
        self.content_keywords = {
            # Financial categories
            'tuition': ['tuition', 'cost', 'fee', 'expense', 'payment', 'billing'],
            'aid': ['financial aid', 'fafsa', 'css profile', 'need-based', 'assistance'],
            'scholarships': ['scholarship', 'grant', 'award', 'merit'],
            'loans': ['loan', 'borrowing', 'repayment', 'debt'],
            'cost_of_living': ['living expense', 'housing cost', 'budget', 'cost of attendance'],
            # Admissions categories
            'requirements': ['prerequisite', 'requirement', 'required course', 'academic preparation'],
            'mcat': ['mcat', 'medical college admission test', 'standardized test'],
            'gpa': ['gpa', 'grade point average', 'academic performance'],
            'timeline': ['timeline', 'deadline', 'important date', 'application cycle'],
            'interview': ['interview', 'mmi', 'multiple mini interview'],
            'selection': ['selection', 'evaluation', 'criteria', 'holistic review']
        }

    def download_pdf(self, url):
        """Download and save PDF files"""
        try:
            if url in self.downloaded_pdfs:
                return
            
            self.logger.info(f"Downloading PDF: {url}")
            
            # Extract filename from URL
            filename = os.path.basename(urlparse(url).path)
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            filepath = os.path.join(self.config.pdf_dir, filename)
            
            # Download PDF
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.downloaded_pdfs.add(url)
            self.logger.info(f"PDF saved to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error downloading PDF {url}: {str(e)}")
            return None

    def should_follow_link(self, url):
        """Enhanced link following logic"""
        if not url.startswith(self.base_url):
            return False
        
        path = urlparse(url).path.lower()
        
        # Always download PDFs
        if path.endswith('.pdf'):
            self.download_pdf(url)
            return False  # Don't try to scrape PDFs as HTML
        
        keywords = [
            'financial', 'tuition', 'scholarship', 'aid', 
            'admissions', 'apply', 'requirements', 'mcat',
            'interview', 'selection', 'timeline', 'prerequisites',
            'curriculum', 'academic'
        ]
        return any(keyword in path for keyword in keywords)

    def get_page(self, url):
        """Enhanced page fetching with better error handling and anti-blocking measures"""
        try:
            self.logger.info(f"Fetching: {url}")
            time.sleep(3)  # Increased delay to avoid blocking
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'TE': 'Trailers',
            }
            
            response = self.session.get(url, headers=headers, timeout=30, allow_redirects=True)
            
            if response.history:
                self.logger.info(f"Redirected from {url} to {response.url}")
                new_path = urlparse(response.url).path
                if new_path not in self.important_paths:
                    self.important_paths.append(new_path)
            
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                alt_paths = [p for p in self.important_paths if p not in url]
                for path in alt_paths:
                    alt_url = urljoin(self.base_url, path)
                    try:
                        alt_response = self.session.get(alt_url, headers=headers, timeout=30)
                        if alt_response.ok:
                            self.logger.info(f"Found alternative path: {alt_url}")
                            return alt_response.text
                    except:
                        continue
            elif e.response.status_code == 429 or e.response.status_code == 403:
                self.logger.warning(f"Rate limited or blocked. Waiting 60 seconds...")
                time.sleep(60)  # Wait longer if blocked
                try:
                    response = self.session.get(url, headers=headers, timeout=30)
                    if response.ok:
                        return response.text
                except:
                    pass
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def extract_content_by_category(self, text, section_title):
        """Enhanced content extraction with both financial and admissions categories"""
        content_type = None
        section_lower = section_title.lower()
        
        # Determine content type based on section title and keywords
        for category, keywords in self.content_keywords.items():
            if any(keyword in section_lower for keyword in keywords):
                content_type = category
                break
        
        # Clean and structure the content
        cleaned_text = self.text_cleaner(text)
        if not cleaned_text:
            return None, None
            
        # Extract specific information based on content type
        if content_type:
            # Financial information extraction
            if content_type in ['tuition', 'aid', 'scholarships', 'loans', 'cost_of_living']:
                amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:per|/)\s*(?:semester|year|term))?', cleaned_text)
                if amounts:
                    cleaned_text = f"Amount Information: {', '.join(amounts)}\n{cleaned_text}"
            
            # Admissions information extraction
            elif content_type == 'requirements':
                requirements = re.findall(r'(?:required|prerequisite):[^.]*\.', cleaned_text, re.I)
                if requirements:
                    cleaned_text = f"Required Courses/Prerequisites: {' '.join(requirements)}\n{cleaned_text}"
                    
            elif content_type == 'mcat':
                scores = re.findall(r'\d{3}(?:\s*-\s*\d{3})?(?:\s*or\s*above)?', cleaned_text)
                if scores:
                    cleaned_text = f"MCAT Scores: {', '.join(scores)}\n{cleaned_text}"
                    
            elif content_type == 'gpa':
                gpas = re.findall(r'\d+\.\d+(?:\s*-\s*\d+\.\d+)?(?:\s*or\s*above)?', cleaned_text)
                if gpas:
                    cleaned_text = f"GPA Requirements: {', '.join(gpas)}\n{cleaned_text}"
                    
            elif content_type == 'timeline':
                dates = re.findall(r'(?:deadline|due date|by)[:\s].*?(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})', cleaned_text)
                if dates:
                    cleaned_text = f"Important Dates: {', '.join(dates)}\n{cleaned_text}"
        
        return content_type, cleaned_text

    def extract_content(self, soup, url):
        """Enhanced content extraction with better categorization"""
        content = {
            'url': url,
            'title': '',
            'intro': [],
            'sections': [],
            'financial_info': {
                'tuition': [],
                'aid': [],
                'scholarships': [],
                'loans': [],
                'cost_of_living': []
            },
            'admissions_info': {
                'requirements': [],
                'mcat': [],
                'gpa': [],
                'timeline': [],
                'interview': [],
                'selection': []
            }
        }
        
        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            content['title'] = self.text_cleaner(title_elem.get_text(strip=True))
        
        # Extract main content
        main_content = soup.find('main') or soup.find('article') or soup
        
        # Process each section
        for section in main_content.find_all(['section', 'div', 'article']):
            # Get section title
            section_title = ''
            header = section.find(['h1', 'h2', 'h3', 'h4'])
            if header:
                section_title = self.text_cleaner(header.get_text(strip=True))
            
            # Get section content
            section_text = ''
            for elem in section.find_all(['p', 'li', 'div']):
                if elem.name == 'div' and not elem.find(['p', 'li']):
                    continue
                text = self.text_cleaner(elem.get_text(strip=True))
                if text:
                    section_text += text + '\n'
            
            if section_text:
                # Categorize and process content
                content_type, processed_text = self.extract_content_by_category(section_text, section_title)
                
                if content_type:
                    if content_type in content['financial_info']:
                        content['financial_info'][content_type].append(processed_text)
                    elif content_type in content['admissions_info']:
                        content['admissions_info'][content_type].append(processed_text)
                else:
                    content['sections'].append({
                        'heading': section_title,
                        'content': section_text
                    })
        
        return content

    def scrape(self):
        """Enhanced scraping method with better content handling"""
        # Start with important pages
        pages_to_visit = [urljoin(self.base_url, path) for path in self.important_paths]
        
        while pages_to_visit:
            url = pages_to_visit.pop(0)
            if url in self.visited_urls:
                continue
            
            # Handle PDFs
            if url.lower().endswith('.pdf'):
                self.download_pdf(url)
                self.visited_urls.add(url)
                continue
            
            html = self.get_page(url)
            if not html:
                continue
            
            self.visited_urls.add(url)
            
            soup = BeautifulSoup(html, 'html.parser')
            content = self.extract_content(soup, url)
            self.content[url] = content
            
            # Find additional relevant links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href and not href.startswith('#'):
                    full_url = urljoin(self.base_url, href)
                    if self.should_follow_link(full_url):
                        pages_to_visit.append(full_url)
            
            self.logger.info(f"Processed: {url}")
            self.logger.info(f"Queue size: {len(pages_to_visit)}")
        
        self.save_results()

    def save_results(self):
        """Enhanced results saving with better organization"""
        # Save raw content
        with open(self.config.raw_file, 'w', encoding='utf-8') as f:
            json.dump(self.content, f, indent=2, ensure_ascii=False)
        
        # Create processed version
        processed_content = {}
        for url, content in self.content.items():
            processed_content[url] = {
                'title': content['title'],
                'text_chunks': []
            }
            
            # Add financial information
            financial_sections = [
                ('Tuition and Fees', content['financial_info']['tuition']),
                ('Financial Aid', content['financial_info']['aid']),
                ('Scholarships and Grants', content['financial_info']['scholarships']),
                ('Loans', content['financial_info']['loans']),
                ('Cost of Living', content['financial_info']['cost_of_living'])
            ]
            
            # Add admissions information
            admissions_sections = [
                ('Academic Requirements', content['admissions_info']['requirements']),
                ('MCAT Information', content['admissions_info']['mcat']),
                ('GPA Requirements', content['admissions_info']['gpa']),
                ('Application Timeline', content['admissions_info']['timeline']),
                ('Interview Process', content['admissions_info']['interview']),
                ('Selection Criteria', content['admissions_info']['selection'])
            ]
            
            # Process all sections
            for section_name, section_content in financial_sections + admissions_sections:
                if section_content:
                    chunk = f"{section_name}\n\n"
                    chunk += '\n\n'.join(section_content)
                    processed_content[url]['text_chunks'].append(chunk)
            
            # Add other content
            if content['intro']:
                chunk = "Introduction\n\n"
                chunk += '\n\n'.join(content['intro'])
                processed_content[url]['text_chunks'].append(chunk)
            
            for section in content['sections']:
                chunk = f"{section['heading']}\n\n{section['content']}"
                processed_content[url]['text_chunks'].append(chunk)
        
        # Save processed content
        with open(self.config.processed_file, 'w', encoding='utf-8') as f:
            json.dump(processed_content, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Raw results saved to {self.config.raw_file}")
        self.logger.info(f"Processed results saved to {self.config.processed_file}")
        if self.downloaded_pdfs:
            self.logger.info(f"Downloaded PDFs saved to {self.config.pdf_dir}")

if __name__ == "__main__":
    output_dir = os.getenv('SCRAPER_OUTPUT_DIR')
    config = ScraperConfig(output_dir)
    scraper = MountSinaiScraper(config)
    scraper.scrape()
