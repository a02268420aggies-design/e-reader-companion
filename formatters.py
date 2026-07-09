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
    Converts PDF text layouts and internal images into isolated items 
    bound inside a fully compliant, highly compressed EPUB container.
    """
    doc = pymupdf.open(pdf_path)
    book = epub.EpubBook()
    
    title_name = os.path.basename(output_path).rsplit('.', 1)[0]
    book.set_title(title_name)
    book.set_language('en')
    
    # We build standard clean XHTML content (WITHOUT base64 images inside the text)
    combined_html = ""
    image_counter = 1
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Get standard layout text fragments
        page_text = page.get_text("html")
        combined_html += page_text
        
        # Extract individual images as separate binary objects to protect e-reader memory
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            img_filename = f"image_{image_counter}.{image_ext}"
            
            # Create a distinct EPUB internal item for the picture asset
            epub_img = epub.EpubImage()
            epub_img.file_name = f"images/{img_filename}"
            epub_img.content = image_bytes
            book.add_item(epub_img)
            
            # Drop a clean, standard tag link directly into the book layout
            combined_html += f'<div style="text-align:center;"><img src="images/{img_filename}" /></div>'
            image_counter += 1
            
    doc.close()
    
    # Clean out any timestamp text artifacts
    cleaned_html = clean_text_content(combined_html)
    
    # Pack text cleanly inside its own dedicated content file
    chapter = epub.EpubHtml(title="Book Content", file_name="content.xhtml", lang="en")
    
    eink_styles = """
    <style>
        body { font-family: sans-serif; line-height: 1.6; padding: 5%; color: #000; background-color: #fff; }
        h1, h2, h3 { text-align: center; margin-top: 1.5em; margin-bottom: 1em; page-break-before: always; }
        img { display: block; max-width: 100%; height: auto; margin: 1.5em auto; }
        p { text-align: justify; margin-bottom: 1.2em; text-indent: 1.2em; }
    </style>
    """
    chapter.content = f"<html><head>{eink_styles}</head><body>{cleaned_html}</body></html>"
    
    book.add_item(chapter)
    book.toc = (chapter,)
    book.spine = ['nav', chapter]
    book.add_item(epub.EpubNav())
    
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