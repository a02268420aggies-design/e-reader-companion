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
    Converts PDF to an EPUB by breaking the book into small, low-memory 
    chunks (every 5 pages) so the Xteink X3 processor never runs out of RAM.
    """
    doc = pymupdf.open(pdf_path)
    book = epub.EpubBook()
    
    title_name = os.path.basename(output_path).rsplit('.', 1)[0]
    book.set_title(title_name)
    book.set_language('en')
    
    eink_styles = """
    <style>
        body { font-family: sans-serif; line-height: 1.6; padding: 3%; color: #000; background-color: #fff; }
        h1, h2, h3 { text-align: center; margin-top: 1.5em; margin-bottom: 1em; }
        img { display: block; max-width: 100%; height: auto; margin: 1.5em auto; }
        p { text-align: justify; margin-bottom: 1.2em; text-indent: 1.2em; }
    </style>
    """
    
    spine = ['nav']
    toc = []
    
    image_counter = 1
    current_chunk_html = ""
    chunk_counter = 1
    
    # Define how many pages to group into a single low-memory file chunk
    PAGES_PER_CHUNK = 5 
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. Extract the text layer for this page
        page_text = page.get_text("html")
        current_chunk_html += page_text
        
        # 2. Extract and link images for this page
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            img_filename = f"image_{image_counter}.{image_ext}"
            
            # Save image as an independent asset item inside the EPUB archive
            epub_img = epub.EpubImage()
            epub_img.file_name = f"images/{img_filename}"
            epub_img.content = image_bytes
            book.add_item(epub_img)
            
            # Inject standard HTML tag reference
            current_chunk_html += f'<div style="text-align:center;"><img src="images/{img_filename}" /></div>'
            image_counter += 1
            
        # 3. If we hit our page limit chunk OR the end of the book, save this section file
        if (page_num + 1) % PAGES_PER_CHUNK == 0 or (page_num + 1) == len(doc):
            cleaned_html = clean_text_content(current_chunk_html)
            
            # Create an independent HTML item inside the book package
            chunk_title = f"Part {chunk_counter}"
            chapter = epub.EpubHtml(title=chunk_title, file_name=f"section_{chunk_counter}.xhtml", lang="en")
            chapter.content = f"<html><head>{eink_styles}</head><body>{cleaned_html}</body></html>"
            
            book.add_item(chapter)
            spine.append(chapter)
            toc.append(chapter)
            
            # Reset temporary chunk cache for the next set of pages
            current_chunk_html = ""
            chunk_counter += 1
            
    doc.close()
    
    # Finalize EPUB navigation structures
    book.toc = tuple(toc)
    book.spine = spine
    book.add_item(epub.EpubNav())
    
    # Save the split book package
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