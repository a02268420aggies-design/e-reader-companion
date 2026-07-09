import os
import re
from PIL import Image
import pypdf
import docx

def clean_extracted_text(text):
    """
    Cleans up typical PDF extraction artifacts like mid-sentence 
    line breaks, weird spacing, and split paragraphs.
    """
    # 1. Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 2. Fix words split by a hyphen at the end of a line (e.g., "for- \n matting" -> "formatting")
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    # 3. Join lines that are part of the same paragraph.
    # If a line doesn't end with a punctuation mark (. ! ?) or a blank line, 
    # it's likely a mid-sentence break.
    cleaned_lines = []
    current_paragraph = []
    
    for line in text.split('\n'):
        stripped_line = line.strip()
        
        if not stripped_line:
            # If it's an empty line, flush the current paragraph
            if current_paragraph:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
            cleaned_lines.append("") # Keep the intentional paragraph break
        else:
            current_paragraph.append(stripped_line)
            # If it ends with sentence-ending punctuation, flush it as a paragraph
            if stripped_line and stripped_line[-1] in ['.', '!', '?', '"', '”']:
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = []
                
    if current_paragraph:
        cleaned_lines.append(" ".join(current_paragraph))
        
    # 4. Collapse multiple consecutive empty spaces or empty lines
    final_text = "\n".join(cleaned_lines)
    final_text = re.sub(r'[ \t]+', ' ', final_text) # collapse extra horizontal spaces
    final_text = re.sub(r'\n{3,}', '\n\n', final_text) # collapse extra vertical lines
    
    return final_text

def convert_pdf_to_txt(pdf_path, output_path):
    """Extracts text from a PDF file and cleans up the layout."""
    reader = pypdf.PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    
    # Run the raw text through our text cleaner
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
    """
    Resizes and converts an image to a sleep-screen compatible grayscale JPEG.
    Adjust target_size to match your Exteink X3's exact resolution.
    """
    with Image.open(image_path) as img:
        # 1. Convert to pure Grayscale
        img = img.convert("L")
        
        # 2. Convert to RGB layout format so JPEG compression accepts it
        img = img.convert("RGB")
        
        # 3. Scale down cleanly
        img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        # 4. Save as .jpg format for sleep screen usage
        img.save(output_path, "JPEG", quality=95)
    return output_path