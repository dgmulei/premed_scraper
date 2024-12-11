# Premed Scraper

A collection of specialized web scrapers designed to extract and clean medical school admissions information. Each scraper is optimized for its specific institution's website structure and content organization.

## Features

### Clean Text Processing
- Advanced text cleaning and normalization
- Smart content structuring
- Semantic relationship preservation
- Optimized for embedding

### Institution-Specific Scrapers

#### Mount Sinai (mtsinai_scraper.py)
- Optimized for Icahn School of Medicine at Mount Sinai's HTML structure
- Extracts:
  * Admissions requirements
  * Application deadlines
  * Program information
  * Contact details
- Maintains content hierarchy
- Preserves contextual relationships

#### AAMC (Coming Soon)
- Will handle PDF documents
- Will process multiple levels of content
- Will maintain document relationships

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Mount Sinai Scraper
```bash
python mtsinai_scraper.py
```

The scraper will:
1. Extract content from Mount Sinai's medical school admissions pages
2. Clean and structure the content
3. Save both raw and processed versions:
   - `scraped_content/raw/mount_sinai_raw.json`
   - `scraped_content/processed/mount_sinai_processed.json`

## Output Structure

### Raw Output
```json
{
    "url": {
        "title": "Page title",
        "intro": ["Introduction paragraphs"],
        "sections": [
            {
                "heading": "Section heading",
                "content": ["Array of paragraphs"]
            }
        ],
        "requirements": ["Array of requirements"],
        "deadlines": ["Array of deadlines"],
        "contact_info": ["Contact information"],
        "links": [
            {
                "text": "Link text",
                "url": "Full URL",
                "context": "Surrounding context"
            }
        ]
    }
}
```

### Processed Output (Embedding-Ready)
```json
{
    "url": {
        "title": "Page title",
        "text_chunks": [
            "Introduction:\n\nIntroductory text",
            "Section Heading\n\nSection content",
            "Requirements and Prerequisites:\n\n• Requirement 1\n• Requirement 2",
            "Important Dates and Deadlines:\n\n• Deadline 1\n• Deadline 2",
            "Contact Information:\n\n• Contact details"
        ]
    }
}
```

## Project Structure

```
premed_scraper/
├── mtsinai_scraper.py     # Mount Sinai specific scraper
├── requirements.txt       # Project dependencies
├── README.md             # Project documentation
└── scraped_content/      # Output directory
    ├── raw/             # Raw JSON output
    └── processed/       # Embedding-ready JSON
```

## Future Development

- Additional institution-specific scrapers
- Automated scraping pipeline
- Enhanced text processing features
- Multi-institution data integration
