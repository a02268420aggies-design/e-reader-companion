import os
import re
from PIL import Image
import pypdf
import docx

def clean_extracted_text(text):
    """
    Advanced text cleaner that strips out Adobe InDesign source tags,
    formats Table of Contents lines cleanly, and forces new chapters 
    to start on fresh pages using Form Feed characters.
    """
    # 1. Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 2. Strip out raw URLs / web links
    url_pattern = r'https?://\S+|www\.\S+'
    text = re.sub(url_pattern, '', text)
    
    # 3. Fix InDesign metadata strings (e.g., "story_text.indd", "chapter1.indd")
    # Matches words or filenames ending in .indd along with surrounding brackets/garbage
    text = re.sub(r'\S*?\.indd\S*', '', text)
    
    # 4. Fix words split by a hyphen at the end of a line
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    cleaned_lines = []
    current_paragraph = []
    
    # Core structural markers
    chapter_markers = ['chapter', 'heading', 'prologue', 'epilogue', 'section', 'part', 'act', 'preface', 'foreword', 'introduction']
    
    for line in text.split('\n'):
        stripped_line = line.strip()
        
        if not stripped_line:
            if current_paragraph:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
            cleaned_lines.append("") 
            continue

        # -- SYSTEM 1: DETECT TABLE OF CONTENTS ENTRIES --
        # Matches lines with dot leaders "..." or lines ending significantly in a page number
        is_toc_line = '...' in stripped_line or re.search(r'\s+\d+$', stripped_line)
        
        # If it looks like a TOC line but is in the middle of a paragraph, flush the paragraph first
        if is_toc_line and not ('chapter' in stripped_line.lower() or any(marker in stripped_line.lower() for marker in chapter_markers)):
            if current_paragraph:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
            
            # Clean up messy TOC layout spacing into a readable format
            cleaned_toc = re.sub(r'\.{2,}', ' . . . . . ', stripped_line)
            cleaned_lines.append(cleaned_toc)
            continue

        # -- SYSTEM 2: DETECT CHAPTERS / PREFACES FOR HARD PAGE BREAKS --
        is_chapter_header = any(
            stripped_line.lower().startswith(marker) for marker in chapter_markers
        ) or re.match(r'^(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})$', stripped_line)
        
        if is_chapter_header:
            if current_paragraph:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
            
            # '\x0c' is the ASCII Form Feed character. E-readers parse this as a clean, hard page break.
            cleaned_lines.append("\x0c") 
            cleaned_lines.append(f"=== {stripped_line.upper()} ===")
            cleaned_lines.append("")
        else:
            current_paragraph.append(stripped_line)
            if stripped_line and stripped_line[-1] in ['.', '!', '?', '"', '”']:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
                
    if current_paragraph:
        cleaned_lines.append(" ".join(current_paragraph))
        
    # 5. Clean up structural spaces and collapse excessive empty blocks
    final_text = "\n".join(cleaned_lines)
    final_text = re.sub(r'[ \t]+', ' ', final_text) 
    final_text = re.sub(r'\n{4,}', '\n\n\n', final_text) 
    
    return final_text

def convert_pdf_to_txt(pdf_path, output_path):
    """Extracts text from a PDF file, scrubs layout artifacts, formats TOC, and splits chapters."""
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