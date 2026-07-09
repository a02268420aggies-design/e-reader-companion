import os
import re
import zipfile
from PIL import Image
import pymupdf
import docx

def clean_text_content(text):
    """Strips out residual footer timestamps from the text stream."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\b[APMpm]{2}\d{1,3}\b', '', text)
    return text

def convert_pdf_to_epub(pdf_path, output_path):
    """
    Converts a PDF into a fully compliant EPUB archive completely natively
    using Python's built-in zipfile engine. Guaranteed stable on Vercel.
    """
    doc = pymupdf.open(pdf_path)
    title_name = os.path.basename(output_path).rsplit('.', 1)[0]
    
    # 1. Setup internal EPUB manifest tracking arrays
    manifest_items = []
    spine_items = []
    sections_content = {}
    images_content = {}
    
    image_counter = 1
    current_chunk_paragraphs = []
    chunk_counter = 1
    PAGES_PER_CHUNK = 8  # Safe chunk size to save Xteink memory
    
    # 2. Extract layout data and process page blocks
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Extract text blocks safely
        text_blocks = page.get_text("blocks")
        for block in text_blocks:
            block_text = block[4].strip()
            if block_text:
                cleaned_block = clean_text_content(block_text)
                if cleaned_block.isdigit() and len(cleaned_block) < 4:
                    continue
                current_chunk_paragraphs.append(f"<p>{cleaned_block}</p>")
                
        # Extract and isolate raw image bytes
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            img_filename = f"image_{image_counter}.{image_ext}"
            images_content[img_filename] = image_bytes
            
            # Append standard relative structural tag
            current_chunk_paragraphs.append(f'<div style="text-align:center; margin: 1em 0;"><img src="{img_filename}" /></div>')
            image_counter += 1
            
        # Compile content array into structured sections
        if (page_num + 1) % PAGES_PER_CHUNK == 0 or (page_num + 1) == len(doc):
            if current_chunk_paragraphs:
                chunk_body = "\n".join(current_chunk_paragraphs)
                file_name = f"section_{chunk_counter}.xhtml"
                
                xhtml_template = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Part {chunk_counter}</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; padding: 5%; color: #000; background-color: #fff; }}
        p {{ text-align: justify; margin-bottom: 1.2em; text-indent: 1.5em; margin-top: 0; }}
        img {{ display: block; max-width: 100%; height: auto; margin: 1.5em auto; }}
    </style>
</head>
<body>
    {chunk_body}
</body>
</html>"""
                sections_content[file_name] = xhtml_template
                manifest_items.append(f'<item id="sec_{chunk_counter}" href="{file_name}" media-type="application/xhtml+xml" />')
                spine_items.append(f'<itemref idref="sec_{chunk_counter}" />')
                
                current_chunk_paragraphs = []
                chunk_counter = 1
                
    doc.close()
    
    # 3. Add extracted image files to manifest track list
    for img_name in images_content.keys():
        ext = img_name.rsplit('.', 1)[1]
        mime = "image/jpeg" if ext in ['jpg', 'jpeg'] else f"image/{ext}"
        manifest_items.append(f'<item id="{img_name}" href="{img_name}" media-type="{mime}" />')

    # 4. Write structural index content manifests
    manifest_str = "\n    ".join(manifest_items)
    spine_str = "\n    ".join(spine_items)
    
    content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>{title_name}</dc:title>
        <dc:language>en</dc:language>
        <dc:identifier id="bookid">urn:uuid:{hash(title_name)}</dc:identifier>
    </metadata>
    <manifest>
        {manifest_str}
    </manifest>
    <spine>
        {spine_str}
    </spine>
</package>"""

    # 5. Pack everything neatly using standard Zip Compression
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
        # Crucial EPUB standard rule: mimetype MUST be written first and uncompressed
        epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        
        # Structure directories mapping
        epub.writestr('META-INF/container.xml', """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>""")
        
        epub.writestr('OEBPS/content.opf', content_opf)
        
        # Write pages
        for f_name, f_body in sections_content.items():
            epub.writestr(f"OEBPS/{f_name}", f_body)
            
        # Write images
        for img_name, img_bytes in images_content.items():
            epub.writestr(f"OEBPS/{img_name}", img_bytes)
            
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
        img = img.convert("L").convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
        img.save(output_path, "JPEG", quality=95)
    return output_path