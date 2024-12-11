# Pre-Med School Content Analysis

A comprehensive tool for analyzing medical school website content and PDF documents to assess coverage of key information categories that pre-med students need.

## Overview

This project provides automated analysis of medical school content to help identify strengths and gaps in how schools present critical information to prospective students. It uses advanced text analysis and GPT-4 to evaluate content coverage across essential categories like admissions requirements, financial information, curriculum details, and more.

## Features

### Smart Content Validation
- Analyzes both website content and PDF documents
- Uses intelligent category mapping with must-include terms
- Calculates content relevance scores
- Prioritizes most relevant content for analysis
- Provides comprehensive coverage assessment

### Key Categories Analyzed
1. Admissions Process & Requirements
   - Application steps and timeline
   - Academic requirements
   - Standardized test requirements
   - Selection criteria
   - Interview process
   - Special programs

2. Financial Information
   - Tuition and fees
   - Financial aid availability
   - Scholarships and grants
   - Loan programs
   - Cost of living considerations
   - Financial planning resources

3. Curriculum & Academic Experience
   - Curriculum overview
   - Pre-clinical and clinical training
   - Learning methods
   - Evaluation systems
   - Academic support
   - Special programs

4. Research & Scholarly Opportunities
   - Research programs
   - Mentorship
   - Research funding
   - Publication opportunities
   - Research facilities
   - Special tracks

5. Clinical Experience & Training
   - Clinical rotation structure
   - Hospital sites
   - Patient interaction
   - Specialty exposure
   - Clinical skills development

6. Student Life & Support
   - Wellness programs
   - Housing
   - Student organizations
   - Mentoring
   - Career counseling
   - Campus facilities

7. Special Programs & Opportunities
   - Dual degree programs
   - Special admission programs
   - Research tracks
   - Global health
   - Community service
   - Leadership development

### Analysis Output
- Coverage assessment (0-100%) for each aspect
- Identified strengths with specific examples
- Gaps in coverage
- Website vs PDF content comparison
- Specific recommendations for improvement

## Components

### Web Scraper
- Scrapes medical school websites
- Handles dynamic content
- Extracts text and metadata
- Processes multiple page types

### PDF Processor
- Extracts text from PDF documents
- Handles nested content structure
- Processes tables and metadata
- Extracts key information

### Smart Coverage Validator
- Filters content by category
- Calculates relevance scores
- Requires must-include terms
- Prioritizes most relevant content
- Generates comprehensive analysis

## Usage

1. Configure the scraper for your target medical school website:
```python
scraper = MtSinaiScraper()
scraper.scrape()
```

2. Process PDF documents:
```python
processor = PDFProcessor()
processor.process_pdfs()
```

3. Run the coverage validator:
```python
validator = SmartPreMedValidator(
    school_name="Mount Sinai",
    web_content_path="scraped_content/processed/mount_sinai_processed.json",
    pdf_content_path="scraped_content/processed/mount_sinai_pdfs_processed.json"
)
results = validator.validate_coverage()
report = validator.generate_report(results)
```

## Requirements
- Python 3.8+
- OpenAI API key (for GPT-4 analysis)
- Required Python packages in requirements.txt

## Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in .env file:
   - OPENAI_API_KEY=your_api_key

## Output
The validator generates a comprehensive report including:
- Executive summary
- Category-by-category analysis
- Coverage assessments
- Identified strengths and gaps
- Specific recommendations

Reports are saved in the reports directory with timestamps for easy reference.

## Project Structure
```
premed_scraper/
├── mtsinai_scraper.py     # Web scraper implementation
├── pdf_processor.py       # PDF processing functionality
├── smart_coverage_validator.py  # Content analysis
├── requirements.txt       # Project dependencies
├── .env                  # Environment variables
├── scraped_content/      # Scraped and processed content
│   └── processed/        # JSON files of processed content
├── reports/              # Generated analysis reports
└── logs/                 # Logging output
```

## Logging
- Detailed logging of all operations
- Progress tracking
- Error handling
- Performance metrics

## Future Improvements
- Support for additional medical schools
- Enhanced PDF table extraction
- More detailed content categorization
- Interactive report generation
- Comparative analysis across schools
