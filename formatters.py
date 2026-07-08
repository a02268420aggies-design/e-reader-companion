import os
from pypdf import PdfReader
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from PIL import Image

def convert_pdf_to_txt(file_path):
    """Extracts raw text from a PDF file page by page."""
    reader = PdfReader(file_path)
    extracted_text = []
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text.append(text.strip())
            
    return "\n\n--- Page Break ---\n\n".join(extracted_text)


def convert_epub_to_txt(file_path):
    """Extracts raw text from an EPUB file by stripping out HTML tags."""
    # Suppress deep ebooklib warning logs to keep console clean
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning)
    
    book = epub.read_epub(file_path)
    extracted_text = []
    
    # EPUBs store book chapters inside individual HTML/XHTML components
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Extract HTML strings and strip away all styling tags using BeautifulSoup
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text()
            
            # Clean up empty lines and trailing paragraph breaks
            cleaned_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
            
            if cleaned_text:
                extracted_text.append(cleaned_text)
                
    return "\n\n".join(extracted_text)


def process_and_save_book(source_path, filename):
    """
    Main pipeline router. Determines the file type, extracts the text,
    or handles image dithering.
    """
    ext = filename.lower().split('.')[-1]
    
    if ext == 'txt':
        with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
            
    elif ext == 'pdf':
        return convert_pdf_to_txt(source_path)
        
    elif ext == 'epub':
        return convert_epub_to_txt(source_path)
        
    elif ext in ['jpg', 'jpeg', 'png', 'bmp']:
        # This returns a PIL Image object instead of raw text string
        return process_image_for_eink(source_path)
        
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

def process_image_for_eink(file_path):
    """
    Resizes an image and applies Floyd-Steinberg dithering 
    to make it display perfectly on a 1-bit E-ink screen.
    """
    with Image.open(file_path) as img:
        # Convert to grayscale first
        img = img.convert('L')
        
        # XTEink X3 target maximum dimensions (preserving aspect ratio so it doesn't stretch)
        target_width = 528
        target_height = 792
        img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Apply 1-bit Floyd-Steinberg Dithering (turns it to crisp pure black & white pixels)
        dithered_img = img.convert('1')
        
        return dithered_img