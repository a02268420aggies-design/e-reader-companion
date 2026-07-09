import os
import re
from PIL import Image
import pymupdf
import docx
from ebooklib import epub

def clean_text_content(html_text):
    """Strips out residual footer timestamps from the text stream."""
    return re.sub(r'\b[APMpm]{2}\d{1,3}\b', '', html_text)

def convert_pdf_to_epub(pdf_path, output_path):
    """
    Converts PDF text layers and inline images directly into a standard 
    reflowable EPUB file that is fully visible on the Xteink X3.
    """
    doc = pymupdf.open(pdf_path)
    book = epub.EpubBook()
    
    # Extract filename without extension to use as the book title
    title_name = os.path.basename(output_path).rsplit('.', 1)[0]
    book.set_title(title_name)
    book.set_language('en')
    
    combined_html = ""
    for page in doc:
        # Pulls structural text alongside embedded base64 images
        combined_html += page.get_text("xhtml")
        
    doc.close()
    
    # Scrub bad text timestamps out of the compiled markup
    cleaned_html = clean_text_content(combined_html)
    
    # Wrap content inside a proper EPUB text chapter
    chapter = epub.EpubHtml(title="Book Content", file_name="content.xhtml", lang="en")
    
    # Inject e-ink layout optimization CSS styles directly into the chapter structure
    eink_styles = """
    <style>
        body { font-family: sans-serif; line-height: 1.6; padding: 5%; color: #000; background-color: #fff; }
        h1, h2, h3 { text-align: center; margin-top: 1.5em; margin-bottom: 1em; page-break-before: always; }
        img { display: block; max-width: 100%; height: auto; margin: 1.5em auto; filter: grayscale(100%); }
        p { text-align: justify; margin-bottom: 1.2em; text-indent: 1.2em; }
    </style>
    """
    chapter.content = f"<html><head>{eink_styles}</head><body>{cleaned_html}</body></html>"
    
    # Bind chapter into the EPUB manifest framework
    book.add_item(chapter)
    book.toc = (chapter,)
    book.spine = ['nav', chapter]
    book.add_item(epub.EpubNav())
    
    # Save the container as a legitimate .epub file
    epub.write_epub(output_path, book, {})
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