import os
import re
from PIL import Image
import pypdf
import docx

def fix_ligatures_and_chars(text):
    """Replaces unmappable PDF ligatures and characters with standard UTF-8 letters."""
    replacements = {
        '\uf005': '',      # Common artifact symbols
        '\uf002': '',
        'ﬁ': 'fi',         # Ligature matching
        'ﬂ': 'fl',
        'ﬀ': 'ff',
        'ﬃ': 'ffi',
        'ﬄ': 'ffl',
        '–': '-',          # En-dash to standard dash
        '—': '—',          # Em-dash
        '‘': "'",          # Smart directional quotes to plain quotes
        '’': "'",
        '“': '"',
        '”': '"',
        '…': '...'
    }
    for bad_char, good_char in replacements.items():
        text = text.replace(bad_char, good_char)
    return text

def clean_extracted_text(text):
    """
    Advanced text cleaner targeting header timestamps, font glyph issues, 
    bulleted Table of Contents layouts, and spacing-based page breaks.
    """
    # 1. Standardize text structure and resolve hidden ligatures
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = fix_ligatures_and_chars(text)
    
    # 2. Strip out raw URLs
    url_pattern = r'https?://\S+|www\.\S+'
    text = re.sub(url_pattern, '', text)
    
    # 3. Wipe out running page timestamp footers (e.g., "10/24/2024 14:32" or "3:15 PM")
    text = re.re = re.sub(r'\b\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?(\s*[APMpm]{2})?\b', '', text)
    text = re.sub(r'\b\d{1,2}:\d{2}\s*[APMpm]{2}\b', '', text)
    
    # 4. Remove Adobe InDesign template markers
    text = re.sub(r'\S*?\.indd\S*', '', text)
    
    # 5. Connect mid-sentence hyphenated line breaks
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    cleaned_lines = []
    current_paragraph = []
    
    # Structural keywords
    chapter_markers = ['chapter', 'heading', 'prologue', 'epilogue', 'section', 'part', 'act', 'preface', 'foreword', 'introduction']
    
    for line in text.split('\n'):
        stripped_line = line.strip()
        
        if not stripped_line:
            if current_paragraph:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
            cleaned_lines.append("") 
            continue

        # -- FORMAT SYSTEM: CLEAN TABLE OF CONTENTS --
        # Detect lines ending with digits (page numbers) or containing dot leaders
        is_toc_line = '...' in stripped_line or re.search(r'\s+\d+$', stripped_line)
        
        if is_toc_line and not any(marker in stripped_line.lower() for marker in chapter_markers):
            if current_paragraph:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
            
            # Remove any ugly dot sequences, strip excess gaps, and format as a bulleted row
            no_dots = re.sub(r'\.{2,}', ' ', stripped_line)
            clean_row = re.sub(r'\s+', ' ', no_dots).strip()
            
            # Format nicely as: "  • Chapter Title (Page Number)"
            match = re.search(r'(.*)\s+(\d+)$', clean_row)
            if match:
                title, page = match.groups()
                cleaned_lines.append(f"  • {title.strip()}  [p. {page}]")
            else:
                cleaned_lines.append(f"  • {clean_row}")
            continue

        # -- PAGE BREAK SYSTEM: CHAPTER DETECTION --
        is_chapter_header = any(
            stripped_line.lower().startswith(marker) for marker in chapter_markers
        ) or re.match(r'^(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})$', stripped_line)
        
        if is_chapter_header:
            if current_paragraph:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
            
            # Force a visual page break using a significant padding break blocks
            cleaned_lines.append("\n\n\n\n\n\n\n\n\n\n") 
            cleaned_lines.append(f"========================================")
            cleaned_lines.append(f"   {stripped_line.upper()}")
            cleaned_lines.append(f"========================================")
            cleaned_lines.append("\n")
        else:
            current_paragraph.append(stripped_line)
            if stripped_line and stripped_line[-1] in ['.', '!', '?', '"', '”']:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
                
    if current_paragraph:
        cleaned_lines.append(" ".join(current_paragraph))
        
    # Final clean-up of spacing blocks
    final_text = "\n".join(cleaned_lines)
    final_text = re.sub(r'[ \t]+', ' ', final_text) 
    final_text = re.sub(r'\n{12,}', '\n\n\n\n\n\n\n\n\n\n', final_text) 
    
    return final_text

def convert_pdf_to_txt(pdf_path, output_path):
    """Extracts text from a PDF file, handles bad characters, cleans up layouts, and builds page splits."""
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