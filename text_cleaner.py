import json
import re
import html

def clean_text(text):
    """Clean text for better embedding quality"""
    # Unescape HTML entities
    text = html.unescape(text)
    
    # Replace multiple newlines/spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize quotes and apostrophes
    text = text.replace('"', '"').replace('"', '"').replace("'", "'")
    
    # Fix common formatting issues
    text = text.replace('toreach', 'to reach')
    text = text.replace('toxicology', 'toxicology')
    text = text.replace('mssm. edu', '@mssm.edu')
    text = text.replace('proc mssm. edures', 'procedures')
    text = text.replace('mssm. education', 'education')
    
    # Remove email addresses and URLs
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove any remaining special characters while preserving sentence structure
    text = re.sub(r'[^\w\s.,!?;:\'"-]', ' ', text)
    
    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Ensure proper spacing after punctuation
    text = re.sub(r'([.,!?;:])\s*', r'\1 ', text)
    
    # Remove navigation-like elements
    text = re.sub(r'Learn More About.*$', '', text)
    text = re.sub(r'See All News.*$', '', text)
    
    # Trim whitespace
    text = text.strip()
    
    return text

def split_long_chunks(text, max_length=800):
    """Split text chunks that are too long at sentence boundaries"""
    if len(text) <= max_length:
        return [text]
        
    # Find sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence)
        if current_length + sentence_length <= max_length:
            current_chunk.append(sentence)
            current_length += sentence_length
        else:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_length = sentence_length
            
    if current_chunk:
        chunks.append(' '.join(current_chunk))
        
    return chunks

def is_boilerplate(text):
    """Check if text is likely boilerplate content"""
    boilerplate_patterns = [
        r'Learn more about',
        r'Click here',
        r'Read more',
        r'Contact us',
        r'Please note',
        r'You can access',
        r'For more information',
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in boilerplate_patterns)

def clean_chunks(chunks):
    """Clean and filter text chunks"""
    cleaned = []
    seen_content = set()  # Track duplicate content
    
    for chunk in chunks:
        # Skip empty chunks
        if not chunk or len(chunk.strip()) < 20:  # Minimum meaningful length
            continue
            
        # Skip boilerplate content
        if is_boilerplate(chunk):
            continue
            
        cleaned_chunk = clean_text(chunk)
        
        # Skip if cleaning resulted in too short text
        if len(cleaned_chunk) < 20:
            continue
            
        # Skip duplicate content
        if cleaned_chunk in seen_content:
            continue
            
        # Split long chunks
        split_chunks = split_long_chunks(cleaned_chunk)
        
        for split_chunk in split_chunks:
            # Skip near-duplicate content (80% similarity threshold)
            if any(len(set(split_chunk.split()) & set(existing.split())) / len(set(split_chunk.split())) > 0.8 
                   for existing in seen_content):
                continue
                
            seen_content.add(split_chunk)
            cleaned.append(split_chunk)
    
    return cleaned

def process_json():
    # Read the existing JSON
    with open('scraped_content/mount_sinai/processed/mount_sinai_processed.json', 'r') as f:
        data = json.load(f)
    
    # Process each URL's content
    cleaned_data = {}
    for url, content in data.items():
        cleaned_data[url] = {
            "title": clean_text(content["title"]),
            "text_chunks": clean_chunks(content["text_chunks"])
        }
    
    # Write cleaned data
    with open('scraped_content/mount_sinai/processed/mount_sinai_processed_clean.json', 'w') as f:
        json.dump(cleaned_data, f, indent=2)

if __name__ == "__main__":
    process_json()
