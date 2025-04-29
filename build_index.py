import json
import re
import pdfplumber
import PyPDF2
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter
import unicodedata
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdf_extraction.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Common academic paper patterns
TITLE_PATTERNS = [
    r"(?i)^[\s\n]*title[\s:]+(.*?)$",
    r"(?i)^[\s\n]*paper title[\s:]+(.*?)$",
    r"(?i)^[\s\n]*(.*?)\n[\s\n]*(?:authors?|by)[\s:]+",
]

AUTHOR_PATTERNS = [
    r"(?i)^[\s\n]*authors?[\s:]+(.*?)$",
    r"(?i)^[\s\n]*by[\s:]+(.*?)$",
    r"(?i)^[\s\n]*(?:presented|written) by[\s:]+(.*?)$",
]

ABSTRACT_PATTERNS = [
    r"(?i)^[\s\n]*abstract[\s:]+(.*?)$",
    r"(?i)^[\s\n]*summary[\s:]+(.*?)$",
    r"(?i)^[\s\n]*synopsis[\s:]+(.*?)$",
]

SECTION_HEADERS = [
    r"(?i)^[\s\n]*introduction[\s:]*$",
    r"(?i)^[\s\n]*1[\s\.]+[\s\n]*introduction",
    r"(?i)^[\s\n]*keywords[\s:]+",
    r"(?i)^[\s\n]*index terms[\s:]+",
]

# Academic organizations and their affiliations - common in author sections
ORG_INDICATORS = [
    "university", "institute", "college", "department", "lab", "laboratory",
    "school", "center", "centre", "corp", "corporation", "inc", "llc",
    "association", "research", "technologies", "systems", "foundation"
]

def normalize_text(text: str) -> str:
    """Normalize text by removing extra whitespace and normalizing unicode characters."""
    if not text:
        return ""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Normalize unicode
    text = unicodedata.normalize('NFKC', text)
    return text.strip()

def clean_author_string(author_text: str) -> str:
    """
    Clean author string by removing emails, footnotes, affiliations in parentheses, etc.
    but preserve author names and basic structure.
    """
    if not author_text:
        return ""
    
    # Remove emails
    author_text = re.sub(r'\b[\w\.-]+@[\w\.-]+\b', '', author_text)
    
    # Remove footnote indicators like [1], [2], etc.
    author_text = re.sub(r'\[\d+\]', '', author_text)
    
    # Remove superscript numbers often used for affiliations
    author_text = re.sub(r'[\d¹²³⁴⁵⁶⁷⁸⁹⁰]+(?=[\s,]|$)', '', author_text)
    
    # Clean up excessive whitespace and commas
    author_text = re.sub(r'\s+', ' ', author_text)
    author_text = re.sub(r',\s*,', ',', author_text)
    author_text = re.sub(r'^\s*,\s*|\s*,\s*$', '', author_text)
    
    return author_text.strip()

def get_largest_font_text(page: pdfplumber.page.Page, max_lines: int = 3) -> List[str]:
    """
    Extract text with the largest font size from a page, likely to be a title.
    Returns a list of lines, limited to max_lines.
    """
    if not page:
        return []
    
    char_data = []
    try:
        # Get character data with position and font info
        char_data = page.chars
    except Exception as e:
        logger.warning(f"Error extracting character data: {e}")
        return []
    
    if not char_data:
        return []
    
    # Group characters by font size and line position
    font_lines = {}
    for char in char_data:
        try:
            font_size = float(char.get('size', 0))
            y_pos = round(float(char.get('top', 0)), 0)  # Round to the nearest point for line grouping
            
            if font_size <= 0:  # Skip invalid font sizes
                continue
                
            if font_size not in font_lines:
                font_lines[font_size] = {}
            
            if y_pos not in font_lines[font_size]:
                font_lines[font_size][y_pos] = []
                
            font_lines[font_size][y_pos].append(char.get('text', ''))
        except (ValueError, TypeError) as e:
            continue
    
    # Sort by font size (largest first)
    sorted_fonts = sorted(font_lines.keys(), reverse=True)
    if not sorted_fonts:
        return []
    
    # Get the largest font size
    largest_font = sorted_fonts[0]
    
    # Get text lines with the largest font size
    text_lines = []
    y_positions = sorted(font_lines[largest_font].keys())
    
    for y_pos in y_positions[:max_lines]:  # Limit to max_lines
        line_text = ''.join(font_lines[largest_font][y_pos])
        text_lines.append(line_text.strip())
    
    # Check if the next largest font is close in size (within 20%)
    # This helps with papers where title might be slightly smaller than headers
    if len(sorted_fonts) > 1:
        next_largest = sorted_fonts[1]
        if next_largest >= largest_font * 0.8:
            # Add these lines as well if they are at the top of the page
            y_positions = sorted(font_lines[next_largest].keys())
            for y_pos in y_positions[:max_lines]:
                # Only add if the y position is near the top of the page
                if min(font_lines[largest_font].keys(), default=1000) + 50 > y_pos:
                    line_text = ''.join(font_lines[next_largest][y_pos])
                    text_lines.append(line_text.strip())
    
    return [line for line in text_lines if line]

def extract_text_between_patterns(text: str, start_pattern: str, end_patterns: List[str]) -> str:
    """Extract text between a start pattern and the first end pattern found."""
    if not text:
        return ""
    
    start_match = re.search(start_pattern, text, re.MULTILINE)
    if not start_match:
        return ""
    
    start_pos = start_match.end()
    end_pos = len(text)
    
    for pattern in end_patterns:
        end_match = re.search(pattern, text[start_pos:], re.MULTILINE)
        if end_match:
            possible_end = start_pos + end_match.start()
            if possible_end < end_pos:
                end_pos = possible_end
    
    return text[start_pos:end_pos].strip()

def extract_metadata_from_pdf(pdf_path: str, doc_id: int) -> Tuple[str, str, str]:
    """
    Extract title, author, and abstract from PDF content using multiple strategies.
    
    Args:
        pdf_path: Path to the PDF file
        doc_id: Document ID for fallback title
    
    Returns:
        Tuple of (title, author, abstract)
    """
    # Default values
    title = f"Document {doc_id + 1}"
    author = "Unknown Author"
    abstract = ""
    
    try:
        # Strategy 1: Extract from PDF metadata using PyPDF2
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if reader.metadata:
                if reader.metadata.get('/Title'):
                    title = reader.metadata.get('/Title')
                if reader.metadata.get('/Author'):
                    author = reader.metadata.get('/Author')
        
        # Strategy 2: Use pdfplumber for text extraction and analysis
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                logger.warning(f"Document {doc_id} has no pages")
                return title, author, abstract
            
            # Extract embedded metadata if not already found
            if pdf.metadata:
                if title == f"Document {doc_id + 1}" and pdf.metadata.get('Title'):
                    title = pdf.metadata.get('Title')
                if author == "Unknown Author" and pdf.metadata.get('Author'):
                    author = pdf.metadata.get('Author')
            
            # Get text from first two pages
            first_page_text = ""
            second_page_text = ""
            
            if len(pdf.pages) > 0:
                first_page_text = pdf.pages[0].extract_text() or ""
            if len(pdf.pages) > 1:
                second_page_text = pdf.pages[1].extract_text() or ""
            
            # Combine text for pattern matching but keep track of page boundaries
            full_text = first_page_text + "\n\n==PAGE_BREAK==\n\n" + second_page_text
            
            # Strategy 3: Font size analysis for title
            title_candidates = get_largest_font_text(pdf.pages[0], max_lines=3)
            if title_candidates:
                potential_title = ' '.join(title_candidates)
                if len(potential_title) > 5 and len(potential_title) < 200:
                    if title == f"Document {doc_id + 1}":  # Only use if we don't have a title yet
                        title = potential_title
            
            # Strategy 4: Pattern matching
            # Try to find title using patterns
            for pattern in TITLE_PATTERNS:
                match = re.search(pattern, full_text, re.MULTILINE)
                if match:
                    potential_title = match.group(1).strip()
                    if len(potential_title) > 5 and len(potential_title) < 200:
                        title = potential_title
                        break
            
            # Find authors using patterns
            for pattern in AUTHOR_PATTERNS:
                match = re.search(pattern, full_text, re.MULTILINE)
                if match:
                    potential_authors = match.group(1).strip()
                    if potential_authors:
                        author = clean_author_string(potential_authors)
                        break
            
            # Find abstract using patterns and extract until the next section header
            for pattern in ABSTRACT_PATTERNS:
                abstract_text = extract_text_between_patterns(full_text, pattern, SECTION_HEADERS)
                if abstract_text:
                    abstract = abstract_text
                    break
            
            # Strategy 5: Positional heuristics if patterns failed
            if author == "Unknown Author":
                lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
                if len(lines) > 2:
                    # Check for author line after title
                    title_index = -1
                    for i, line in enumerate(lines):
                        if normalize_text(line).lower() == normalize_text(title).lower():
                            title_index = i
                            break
                    
                    if title_index >= 0 and title_index + 1 < len(lines):
                        # Author is likely the line after title
                        potential_author = lines[title_index + 1]
                        # Author lines typically don't have these words
                        if not any(word in potential_author.lower() for word in ["journal", "conference", "proceedings", "volume"]):
                            author = clean_author_string(potential_author)
            
            # If abstract wasn't found through patterns
            if not abstract:
                # Look for the first paragraph after title and author that's not too short
                lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
                abstract_start = -1
                for i, line in enumerate(lines):
                    if "abstract" in line.lower():
                        abstract_start = i
                        break
                
                if abstract_start >= 0 and abstract_start + 1 < len(lines):
                    abstract_lines = []
                    for line in lines[abstract_start + 1:]:
                        if any(re.match(pattern, line) for pattern in SECTION_HEADERS):
                            break
                        abstract_lines.append(line)
                    abstract = " ".join(abstract_lines)
                
                # If still no abstract, use the first substantial paragraph after title and author
                if not abstract and len(lines) > 3:
                    for i in range(2, min(10, len(lines))):
                        if len(lines[i]) > 100:  # Likely a paragraph
                            abstract = lines[i]
                            break
            
            # Normalize and limit abstract length to 500 chars (but at complete sentences)
            if abstract:
                abstract = normalize_text(abstract)
                if len(abstract) > 500:
                    # Try to cut at a sentence boundary
                    end_pos = abstract[:500].rfind('.')
                    if end_pos > 0:
                        abstract = abstract[:end_pos+1]
                    else:
                        abstract = abstract[:500]
    
    except Exception as e:
        logger.error(f"Error extracting metadata from PDF {pdf_path}: {e}")
    
    # Final cleanup and validation
    title = normalize_text(title)
    author = normalize_text(author)
    abstract = normalize_text(abstract)
    
    # Validate title (basic check)
    if len(title) < 5 or len(title) > 300:
        title = f"Document {doc_id + 1}"
    
    return title, author, abstract

def build_index(data_dir: str, index_path: str, metadata_path: str):
    """
    Build inverted index and metadata for PDF documents in data_dir.
    
    Args:
        data_dir: Directory containing PDF files
        index_path: Path to save inverted_index.json
        metadata_path: Path to save document_metadata.json
    """
    data_dir = Path(data_dir)
    index_dir = Path(index_path).parent
    index_dir.mkdir(exist_ok=True)
    
    inverted_index = {
        'any': {},
        'title': {},
        'author': {},
        'abstract': {}
    }
    metadata = {}
    
    pdf_files = list(data_dir.glob("*.pdf"))
    total_files = len(pdf_files)
    logger.info(f"Found {total_files} PDF files to process")
    
    start_time = time.time()
    
    # Process each PDF
    for doc_id, doc_path in enumerate(pdf_files):
        try:
            logger.info(f"Processing {doc_id+1}/{total_files}: {doc_path.name}")
            file_start_time = time.time()
            
            # Extract metadata
            title, author, abstract = extract_metadata_from_pdf(str(doc_path), doc_id)
            
            # Extract content for indexing
            content = ""
            try:
                with pdfplumber.open(doc_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            content += text + "\n"
            except Exception as e:
                logger.error(f"Error extracting text from {doc_path}: {e}")
                # If we can't extract content, use the metadata we have
                content = f"{title} {author} {abstract}"
            
            # Store metadata
            metadata[str(doc_id)] = {
                'title': title,
                'author': author,
                'abstract': abstract,
                'file_path': str(doc_path)
            }
            
            # Index content
            tokens = re.findall(r'\w+', content.lower())
            
            # Build inverted index for 'any' field
            for pos, term in enumerate(tokens):
                if len(term) < 2:  # Skip very short terms
                    continue
                if term not in inverted_index['any']:
                    inverted_index['any'][term] = {}
                if str(doc_id) not in inverted_index['any'][term]:
                    inverted_index['any'][term][str(doc_id)] = []
                inverted_index['any'][term][str(doc_id)].append(pos)
            
            # Index title
            title_tokens = re.findall(r'\w+', title.lower())
            for pos, term in enumerate(title_tokens):
                if len(term) < 2:  # Skip very short terms
                    continue
                if term not in inverted_index['title']:
                    inverted_index['title'][term] = {}
                if str(doc_id) not in inverted_index['title'][term]:
                    inverted_index['title'][term][str(doc_id)] = []
                inverted_index['title'][term][str(doc_id)].append(pos)
            
            # Index author
            author_tokens = re.findall(r'\w+', author.lower())
            for pos, term in enumerate(author_tokens):
                if len(term) < 2:  # Skip very short terms
                    continue
                if term not in inverted_index['author']:
                    inverted_index['author'][term] = {}
                if str(doc_id) not in inverted_index['author'][term]:
                    inverted_index['author'][term][str(doc_id)] = []
                inverted_index['author'][term][str(doc_id)].append(pos)
            
            # Index abstract
            abstract_tokens = re.findall(r'\w+', abstract.lower())
            for pos, term in enumerate(abstract_tokens):
                if len(term) < 2:  # Skip very short terms
                    continue
                if term not in inverted_index['abstract']:
                    inverted_index['abstract'][term] = {}
                if str(doc_id) not in inverted_index['abstract'][term]:
                    inverted_index['abstract'][term][str(doc_id)] = []
                inverted_index['abstract'][term][str(doc_id)].append(pos)
            
            file_elapsed = time.time() - file_start_time
            logger.info(f"Processed {doc_path.name} in {file_elapsed:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error processing {doc_path}: {e}")
            continue
    
    # Save inverted index and metadata
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(inverted_index, f)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Index built successfully: {len(metadata)} documents indexed in {elapsed_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error saving index files: {e}")

if __name__ == "__main__":
    from pathlib import Path
    BASE_DIR = Path(__file__).parent
    DATA_DIR = Path(r"D:\Mphil CS\IRS\Assignment\PDFs 1-250")  # Update to your PDF folder
    INDEX_PATH = BASE_DIR / "index_files" / "inverted_index.json"
    METADATA_PATH = BASE_DIR / "index_files" / "document_metadata.json"
    
    build_index(DATA_DIR, INDEX_PATH, METADATA_PATH)