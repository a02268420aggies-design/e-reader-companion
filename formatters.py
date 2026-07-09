import os
import re
from PIL import Image
import pypdf
import docx

def clean_extracted_text(text):
    """
    Cleans up typical PDF extraction artifacts like mid-sentence 
    line breaks, weird spacing, url codes, and split paragraphs, 
    while keeping chapters organized.
    """
    # 1. Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 2. Strip out raw URLs / web links embedded in text strings
    # Catches http, https, ftp, and raw www links
    url_pattern = r'https?://\S+|www\.\S+'
    text = re.sub(url_pattern, '', text)
    
    # 3. Fix words split by a hyphen at the end of a line (e.g., "for- \n matting" -> "formatting")
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    cleaned_lines = []
    current_paragraph = []
    
    # Common words that signal a new section/chapter break
    chapter_markers = ['chapter', 'heading', 'prologue', 'epilogue', 'section', 'part', 'act']
    
    for line in text.split('\n'):
        stripped_line = line.strip()
        
        if not stripped_line:
            # Empty line -> Flush the previous paragraph
            if current_paragraph:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
            cleaned_lines.append("") 
            continue

        # Check if this line looks like a Chapter Header (e.g., "Chapter 1", "CHAPTER IV")
        is_chapter_header = any(
            stripped_line.lower().startswith(marker) for marker in chapter_markers
        ) or re.match(r'^(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})$', stripped_line) # Roman numerals check
        
        if is_chapter_header:
            # Flush whatever paragraph we were building before the chapter
            if current_paragraph:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
            
            # Add breathing room around the chapter title
            cleaned_lines.append("\n")
            cleaned_lines.append(f"--- {stripped_line.upper()} ---")
            cleaned_lines.append("\n")
        else:
            current_paragraph.append(stripped_line)
            # End of a structural sentence -> flush it as a cohesive block
            if stripped_line and stripped_line[-1] in ['.', '!', '?', '"', '”']:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
                
    if current_paragraph:
        cleaned_lines.append(" ".join(current_paragraph))
        
    # 4. Collapse consecutive whitespace blocks cleanly
    final_text = "\n".join(cleaned_lines)
    final_text = re.sub(r'[ \t]+', ' ', final_text)  # Extra spaces -> single space
    final_text = re.sub(r'\n{4,}', '\n\n\n', final_text) # Soft cap vertical gaps
    
    return final_text

def convert_pdf_to_txt(pdf_path, output_path):
    """Extracts text from a PDF file, scrubs URLs, and formats chapters."""
    reader = pypdf.PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    
    cleaned_text = clean_extracted_text(text)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    return output_path

def convert_docx_to_txt(docx_path, output_path):
    """Extracts raw text from a DOCX file."""
    doc = docx.Document(docx_path)
    text = [para.text for para in doc.paragraphs]
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(text))
    return output_path

def process_eink_image(image_path, output_path, target_size=(1404, 1872)):
    """Resizes and converts an image to a sleep-screen compatible grayscale JPEG."""
    with Image.open(image_path) as img:
        img = img.convert("L")
        img = img.convert("RGB")
        img = img.resize(target_size, Image.Resampling.LANCZOS)
        img.save(output_path, "JPEG", quality=95)
    return output_path