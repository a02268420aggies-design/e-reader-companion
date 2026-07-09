import os
from PIL import Image
import pypdf # or pdfplumber
import docx

def convert_pdf_to_txt(pdf_path, output_path):
    """Extracts raw text from a PDF file."""
    reader = pypdf.PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
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
    Resizes and converts an image to grayscale.
    Adjust target_size to match your Exteink X3's exact resolution.
    """
    with Image.open(image_path) as img:
        # Convert to grayscale (L mode is perfect for e-ink screens)
        img = img.convert("L")
        # Resize to fit the screen nicely
        img = img.resize(target_size, Image.Resampling.LANCZOS)
        img.save(output_path, "PNG") # PNG or BMP usually work best for sleep screens
    return output_path