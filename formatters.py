import os
import re
from PIL import Image
import pymupdf  # Replaces pypdf for high-fidelity HTML layout processing
import docx

def clean_html_artifacts(html_content):
    """
    Cleans residual timestamp text fragments and normalizes text properties 
    so it displays nicely on e-ink reading screens.
    """
    # 1. Clear residual timestamp fragments (e.g. ghost "PM8", "AM13" artifacts)
    html_content = re.sub(r'\b[APMpm]{2}\d{1,3}\b', '', html_content)
    
    # 2. Inject CSS directly into the HTML header to optimize layout for e-ink
    # Forces hard page breaks before structural heading markers <h1>, <h2>, etc.
    eink_css = """
    <style>
        body { font-family: sans-serif; line-height: 1.6; padding: 5%; color: #000; background-color: #fff; }
        h1, h2, h3 { page-break-before: always; text-align: center; margin-top: 2em; margin-bottom: 1em; }
        img { display: block; max-width: 100%; height: auto; margin: 1.5em auto; filter: grayscale(100%); }
        p { text-align: justify; margin-bottom: 1.2em; text-indent: 1.5em; }
        ul, ol { margin-bottom: 1.2em; padding-left: 2em; }
    </style>
    """
    
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", f"{eink_css}</head>")
    else:
        html_content = eink_css + html_content
        
    return html_content

def convert_pdf_to_txt(pdf_path, output_path):
    """
    Converts PDF to structural XHTML layouts with native base64 embedded images.
    Note: 'output_path' will be saved as an .html asset file.
    """
    doc = pymupdf.open(pdf_path)
    combined_html = "<html><head><meta charset='utf-8'></head><body>"
    
    # Iterate through layout layers, extracting structural text flow alongside image embeds
    for page in doc:
        # 'xhtml' format extracts text blocks AND embeds images as self-contained base64 strings
        page_html = page.get_text("xhtml")
        combined_html += page_html
        
    combined_html += "</body></html>"
    doc.close()
    
    # Run structural text cleaner to eliminate ghost timestamps
    final_html = clean_html_artifacts(combined_html)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)
        
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
        img = img.convert("L").convert("RGB")
        img = img.resize(target_size, Image.Resampling.LANCZOS)
        img.save(output_path, "JPEG", quality=95)
    return output_path