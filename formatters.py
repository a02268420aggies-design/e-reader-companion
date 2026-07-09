import os
import re
from PIL import Image
import pymupdf
import docx
from ebooklib import epub

def clean_text_content(text):
    """Cleans up bad characters, structural fragments, and running footers."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Clean out residual timestamp strings
    text = re.sub(r'\b[APMpm]{2}\d{1,3}\b', '', text)
    return text

def convert_pdf_to_epub(pdf_path, output_path):
    """
    Converts PDF text layers and image streams into structural, 
    highly optimized, bulletproof EPUB blocks for low-memory devices.
    """
    doc = pymupdf.open(pdf_path)
    book = epub.EpubBook()
    
    title_name = os.path.basename(output_path).rsplit('.', 1)[0]
    book.set_title(title_name)
    book.set_language('en')
    
    # Simple, high-contrast structural styling rules
    eink_styles = """
    body { font-family: sans-serif; line-height: 1.6; padding: 5%; color: #000; background-color: #fff; }
    p { text-align: justify; margin-bottom: 1.2em; text-indent: 1.5em; margin-top: 0; }
    h1, h2, h3 { text-align: center; margin-top: 1.5em; margin-bottom: 1em; }
    img { display: block; max-width: 100%; height: auto; margin: 1.5em auto; }
    """
    
    # Create the global stylesheet asset item
    style_item = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=eink_styles)
    book.add_item(style_item)
    
    spine = ['nav']
    toc = []
    
    image_counter = 1
    current_chunk_paragraphs = []
    chunk_counter = 1
    PAGES_PER_CHUNK = 8 # Safe pagination block to limit device RAM usage
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. Pull the raw structural string blocks instead of complex layout code matrices
        text_blocks = page.get_text("blocks")
        for block in text_blocks:
            block_text = block[4].strip()
            if block_text:
                cleaned_block = clean_text_content(block_text)
                # Eliminate floating page number artifacts from being grouped as long text blocks
                if cleaned_block.isdigit() and len(cleaned_block) < 4:
                    continue
                # Wrap clean rows inside standard paragraph wrappers
                current_chunk_paragraphs.append(f"<p>{cleaned_block}</p>")
                
        # 2. Extract and link standalone image data bytes
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            img_filename = f"image_{image_counter}.{image_ext}"
            
            epub_img = epub.EpubImage()
            epub_img.file_name = f"images/{img_filename}"
            epub_img.content = image_bytes
            book.add_item(epub_img)
            
            current_chunk_paragraphs.append(f'<div style="text-align:center;"><img src="images/{img_filename}" /></div>')
            image_counter += 1
            
        # 3. Compile layout data chunk into isolated manifest containers
        if (page_num + 1) % PAGES_PER_CHUNK == 0 or (page_num + 1) == len(doc):
            if current_chunk_paragraphs:
                chunk_body = "\n".join(current_chunk_paragraphs)
                
                chunk_title = f"Part {chunk_counter}"
                chapter = epub.EpubHtml(title=chunk_title, file_name=f"section_{chunk_counter}.xhtml", lang="en")
                
                # Link explicitly to our style item item sheet layout
                chapter.content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{chunk_title}</title>
    <link rel="stylesheet" href="style/nav.css" type="text/css" />
</head>
<body>
    {chunk_body}
</body>
</html>"""
                
                book.add_item(chapter)
                spine.append(chapter)
                toc.append(chapter)
                
                # Reset buffers
                current_chunk_paragraphs = []
                chunk_counter += 1
                
    doc.close()
    
    # Finalize navigation parameters
    book.toc = tuple(toc)
    book.spine = spine
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())
    
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