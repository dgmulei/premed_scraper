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
        
        # Create directories if they don't exist
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
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
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
        # Updated financial paths based on actual site structure
        self.financial_paths = [
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
            '/education/medical/financial-aid'
        ]
        
        # Financial content keywords
        self.financial_keywords = {
            'tuition': ['tuition', 'cost', 'fee', 'expense', 'payment', 'billing'],
            'aid': ['financial aid', 'fafsa', 'css profile', 'need-based', 'assistance'],
            'scholarships': ['scholarship', 'grant', 'award', 'merit'],
            'loans': ['loan', 'borrowing', 'repayment', 'debt'],
            'cost_of_living': ['living expense', 'housing cost', 'budget', 'cost of attendance']
        }

    def should_follow_link(self, url):
        """Determine if a link should be followed"""
        if not url.startswith(self.base_url):
            return False
        path = urlparse(url).path.lower()
        return any(keyword in path for keyword in ['financial', 'tuition', 'scholarship', 'aid', 'admissions'])

    def get_page(self, url):
        """Enhanced page fetching with better error handling"""
        try:
            self.logger.info(f"Fetching: {url}")
            time.sleep(2)  # Respectful delay
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            # Follow redirects to handle alternative paths
            response = self.session.get(url, headers=headers, timeout=30, allow_redirects=True)
            
            if response.history:
                self.logger.info(f"Redirected from {url} to {response.url}")
                # Add new financial paths if discovered
                if any(keyword in response.url.lower() for keyword in ['financial', 'tuition', 'scholarship', 'aid']):
                    new_path = urlparse(response.url).path
                    if new_path not in self.financial_paths:
                        self.financial_paths.append(new_path)
            
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Try alternative paths
                alt_paths = [p for p in self.financial_paths if p not in url]
                for path in alt_paths:
                    alt_url = urljoin(self.base_url, path)
                    try:
                        alt_response = self.session.get(alt_url, headers=headers, timeout=30)
                        if alt_response.ok:
                            self.logger.info(f"Found alternative path: {alt_url}")
                            return alt_response.text
                    except:
                        continue
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def extract_financial_content(self, text, section_title):
        """Enhanced financial content extraction"""
        content_type = None
        
        # Determine content type based on section title and keywords
        section_lower = section_title.lower()
        for category, keywords in self.financial_keywords.items():
            if any(keyword in section_lower for keyword in keywords):
                content_type = category
                break
        
        # Clean and structure the content
        cleaned_text = self.text_cleaner(text)
        if not cleaned_text:
            return None, None
            
        # Extract specific financial information
        if content_type == 'tuition':
            # Look for currency amounts and semester/year indicators
            amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:per|/)\s*(?:semester|year|term))?', cleaned_text)
            if amounts:
                cleaned_text = f"Tuition and Fees: {', '.join(amounts)}\n{cleaned_text}"
                
        elif content_type == 'aid':
            # Look for application deadlines and requirements
            deadlines = re.findall(r'(?:deadline|due|by)[:\s].*?(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})', cleaned_text)
            if deadlines:
                cleaned_text = f"Important Deadlines: {', '.join(deadlines)}\n{cleaned_text}"
                
        elif content_type == 'scholarships':
            # Look for award amounts and eligibility criteria
            awards = re.findall(r'(?:award|scholarship)[:\s].*?(?:\$[\d,]+(?:\.\d{2})?|full tuition)', cleaned_text)
            if awards:
                cleaned_text = f"Available Awards: {', '.join(awards)}\n{cleaned_text}"
        
        return content_type, cleaned_text

    def extract_content(self, soup, url):
        """Enhanced content extraction with better financial information handling"""
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
            'requirements': [],
            'deadlines': [],
            'contact_info': []
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
                # Check if this is financial content
                content_type, processed_text = self.extract_financial_content(section_text, section_title)
                
                if content_type and processed_text:
                    content['financial_info'][content_type].append(processed_text)
                else:
                    content['sections'].append({
                        'heading': section_title,
                        'content': section_text
                    })
        
        return content

    def scrape(self):
        """Enhanced scraping method with better financial content handling"""
        # Start with financial aid pages
        pages_to_visit = [urljoin(self.base_url, path) for path in self.financial_paths]
        
        # Add other important pages
        pages_to_visit.extend([
            f"{self.base_url}/education/medical/admissions",
            f"{self.base_url}/education/medical/curriculum-program",
            f"{self.base_url}/education/medical/student-affairs"
        ])
        
        while pages_to_visit:
            url = pages_to_visit.pop(0)
            if url in self.visited_urls:
                continue
            
            html = self.get_page(url)
            if not html:
                continue
            
            self.visited_urls.add(url)
            
            soup = BeautifulSoup(html, 'html.parser')
            content = self.extract_content(soup, url)
            self.content[url] = content
            
            # Find additional financial aid related links
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
        """Enhanced results saving with better financial information organization"""
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
            
            # Add financial information first
            financial_sections = [
                ('Tuition and Fees', content['financial_info']['tuition']),
                ('Financial Aid', content['financial_info']['aid']),
                ('Scholarships and Grants', content['financial_info']['scholarships']),
                ('Loans', content['financial_info']['loans']),
                ('Cost of Living', content['financial_info']['cost_of_living'])
            ]
            
            for section_name, section_content in financial_sections:
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

if __name__ == "__main__":
    output_dir = os.getenv('SCRAPER_OUTPUT_DIR')
    config = ScraperConfig(output_dir)
    scraper = MountSinaiScraper(config)
    scraper.scrape()
