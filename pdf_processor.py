import os
import re
import json
import logging
import pdfplumber
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, pdf_dir):
        self.pdf_dir = pdf_dir
        self.processed_dir = os.path.join(os.path.dirname(pdf_dir), 'processed_pdfs')
        self.merged_output_path = os.path.join(os.path.dirname(pdf_dir), 'processed', 'mount_sinai_pdfs_processed.json')
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.merged_output_path), exist_ok=True)
        
        # PDF type patterns
        self.pdf_patterns = {
            'financial': {
                'coa': r'COA\.pdf$|Cost.+Attendance',
                'scholarship': r'Scholar|Award',
                'budget': r'Budget',
                'aid': r'Aid|FAFSA'
            },
            'admissions': {
                'requirements': r'Requirements|Prerequisites',
                'policies': r'Policies|Procedures',
                'program_info': r'Program|Curriculum',
                'timeline': r'Timeline|Schedule'
            }
        }
    
    def determine_pdf_type(self, filename):
        """Determine the type and subtype of a PDF based on its filename"""
        for doc_type, subtypes in self.pdf_patterns.items():
            for subtype, pattern in subtypes.items():
                if re.search(pattern, filename, re.IGNORECASE):
                    return doc_type, subtype
        return 'other', 'general'
    
    def extract_tables(self, page):
        """Extract and clean tables from a PDF page"""
        try:
            tables = page.extract_tables()
            cleaned_tables = []
            
            for table in tables:
                # Remove empty rows and cells
                cleaned_table = [
                    [cell.strip() if isinstance(cell, str) else cell for cell in row if cell]
                    for row in table if any(cell for cell in row)
                ]
                if cleaned_table:
                    cleaned_tables.append(cleaned_table)
            
            return cleaned_tables
        except Exception as e:
            logger.warning(f"Error extracting tables: {str(e)}")
            return []
    
    def extract_financial_data(self, text, tables):
        """Extract financial information from text and tables"""
        financial_data = {
            'amounts': [],
            'deadlines': [],
            'requirements': []
        }
        
        try:
            # Extract dollar amounts
            amounts = re.findall(r'\$\s*[\d,]+(?:\.\d{2})?(?:\s*(?:per|/)\s*(?:semester|year|term))?', text)
            financial_data['amounts'].extend(amounts)
            
            # Extract deadlines
            deadlines = re.findall(r'(?:deadline|due date|by)[:\s].*?(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})', text)
            financial_data['deadlines'].extend(deadlines)
            
            # Extract requirements
            requirements = re.findall(r'(?:required|must submit|need to)[^.]*\.', text)
            financial_data['requirements'].extend(requirements)
        except Exception as e:
            logger.warning(f"Error extracting financial data: {str(e)}")
        
        return financial_data
    
    def extract_admissions_data(self, text, tables):
        """Extract admissions information from text and tables"""
        admissions_data = {
            'requirements': [],
            'deadlines': [],
            'mcat_scores': [],
            'gpa_info': []
        }
        
        try:
            # Extract MCAT scores
            mcat_scores = re.findall(r'\d{3}(?:\s*-\s*\d{3})?(?:\s*or\s*above)?', text)
            admissions_data['mcat_scores'].extend(mcat_scores)
            
            # Extract GPA information
            gpa_info = re.findall(r'\d+\.\d+(?:\s*-\s*\d+\.\d+)?(?:\s*or\s*above)?', text)
            admissions_data['gpa_info'].extend(gpa_info)
            
            # Extract requirements
            requirements = re.findall(r'(?:required|prerequisite):[^.]*\.', text)
            admissions_data['requirements'].extend(requirements)
            
            # Extract deadlines
            deadlines = re.findall(r'(?:deadline|due date|by)[:\s].*?(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})', text)
            admissions_data['deadlines'].extend(deadlines)
        except Exception as e:
            logger.warning(f"Error extracting admissions data: {str(e)}")
        
        return admissions_data
    
    def create_chunks(self, text, chunk_size=512, overlap=50):
        """Create overlapping chunks of text for embedding"""
        try:
            words = text.split()
            chunks = []
            
            for i in range(0, len(words), chunk_size - overlap):
                chunk = ' '.join(words[i:i + chunk_size])
                if chunk:
                    chunks.append(chunk)
            
            return chunks
        except Exception as e:
            logger.warning(f"Error creating chunks: {str(e)}")
            return [text] if text else []
    
    def process_pdf(self, pdf_path):
        """Process a single PDF file"""
        filename = os.path.basename(pdf_path)
        doc_type, subtype = self.determine_pdf_type(filename)
        
        logger.info(f"Processing {filename} (Type: {doc_type}, Subtype: {subtype})")
        
        processed_data = {
            'metadata': {
                'filename': filename,
                'type': doc_type,
                'subtype': subtype
            },
            'content': {
                'text': [],
                'tables': [],
                'extracted_data': {},
                'chunks': []
            }
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract text
                        text = page.extract_text() or ""
                        full_text += text + "\n\n"
                        processed_data['content']['text'].append({
                            'page': page_num,
                            'text': text
                        })
                        
                        # Extract tables
                        tables = self.extract_tables(page)
                        if tables:
                            processed_data['content']['tables'].append({
                                'page': page_num,
                                'tables': tables
                            })
                    except Exception as e:
                        logger.warning(f"Error processing page {page_num} in {filename}: {str(e)}")
                        continue
                
                # Extract specific data based on document type
                if doc_type == 'financial':
                    processed_data['content']['extracted_data'] = self.extract_financial_data(
                        full_text,
                        [t['tables'] for t in processed_data['content']['tables']]
                    )
                elif doc_type == 'admissions':
                    processed_data['content']['extracted_data'] = self.extract_admissions_data(
                        full_text,
                        [t['tables'] for t in processed_data['content']['tables']]
                    )
                
                # Create chunks for embedding
                chunks = self.create_chunks(full_text)
                processed_data['content']['chunks'] = [
                    {
                        'text': chunk,
                        'metadata': {
                            'doc_type': doc_type,
                            'subtype': subtype,
                            'filename': filename
                        }
                    }
                    for chunk in chunks
                ]
                
                # Save individual processed data
                output_path = os.path.join(
                    self.processed_dir,
                    f"{os.path.splitext(filename)[0]}_processed.json"
                )
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Successfully processed {filename}")
                return processed_data
                
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            return None
    
    def process_all_pdfs(self):
        """Process all PDFs and create merged output"""
        results = {
            'processed_files': [],
            'failed_files': [],
            'summary': {
                'financial': {'count': 0, 'files': []},
                'admissions': {'count': 0, 'files': []},
                'other': {'count': 0, 'files': []}
            }
        }
        
        # Dictionary to hold all processed PDF data
        merged_content = {}
        
        total_pdfs = len([f for f in os.listdir(self.pdf_dir) if f.lower().endswith('.pdf')])
        processed_count = 0
        
        for pdf_file in os.listdir(self.pdf_dir):
            if pdf_file.lower().endswith('.pdf'):
                processed_count += 1
                logger.info(f"Processing PDF {processed_count}/{total_pdfs}: {pdf_file}")
                
                pdf_path = os.path.join(self.pdf_dir, pdf_file)
                processed_data = self.process_pdf(pdf_path)
                
                if processed_data:
                    results['processed_files'].append(pdf_file)
                    doc_type = processed_data['metadata']['type']
                    results['summary'][doc_type]['count'] += 1
                    results['summary'][doc_type]['files'].append(pdf_file)
                    
                    # Add to merged content
                    merged_content[pdf_file] = processed_data
                else:
                    results['failed_files'].append(pdf_file)
        
        # Save processing summary
        summary_path = os.path.join(self.processed_dir, 'processing_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save merged content
        with open(self.merged_output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_content, f, indent=2, ensure_ascii=False)
        
        # Log summary
        logger.info("\nPDF Processing Summary:")
        logger.info(f"Total processed: {len(results['processed_files'])}")
        logger.info(f"Failed: {len(results['failed_files'])}")
        logger.info("\nBy Category:")
        for category, data in results['summary'].items():
            logger.info(f"{category.title()}: {data['count']} files")
        
        if results['failed_files']:
            logger.warning("\nFailed files:")
            for failed_file in results['failed_files']:
                logger.warning(f"- {failed_file}")
        
        logger.info(f"\nMerged content saved to: {self.merged_output_path}")
        return results

if __name__ == "__main__":
    # Get the PDF directory from the scraper's output
    pdf_dir = os.path.join('scraped_content', 'pdfs')
    
    # Process PDFs
    processor = PDFProcessor(pdf_dir)
    results = processor.process_all_pdfs()
