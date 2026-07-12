import os
import re
import zipfile
import pymupdf
import docx
from PIL import Image, ImageOps

def clean_text_content(text):
    """Strips out residual footer timestamps from the text stream."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\b[APMpm]{2}\d{1,3}\b', '', text)
    return text

def convert_pdf_to_epub(pdf_path, output_path):
    """
    Converts a PDF into an EPUB by scanning text for 'Chapter' milestones,
    creating natural book section breaks instead of arbitrary page cutoffs.
    """
    doc = pymupdf.open(pdf_path)
    title_name = os.path.basename(output_path).rsplit('.', 1)[0]
    
    manifest_items = []
    spine_items = []
    ncx_items = []
    sections_content = {}
    images_content = {}
    
    image_counter = 1
    current_chunk_paragraphs = []
    chunk_counter = 1
    
    chapter_regex = re.compile(r'^\s*(chapter|section)\s+(\d+|[ivxlcdm]+|one|two|three|four|five|six|seven|eight|nine|ten)\b', re.IGNORECASE)

    for page_num in range(len(doc)):
        page = doc[page_num]
        text_blocks = page.get_text("blocks")
        
        for block in text_blocks:
            block_text = block[4].strip()
            if not block_text:
                continue
                
            cleaned_block = clean_text_content(block_text)
            
            if cleaned_block.isdigit() and len(cleaned_block) < 4:
                continue
            
            if chapter_regex.match(cleaned_block):
                if current_chunk_paragraphs:
                    chunk_body = "\n".join(current_chunk_paragraphs)
                    file_name = f"section_{chunk_counter}.xhtml"
                    
                    xhtml_template = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter {chunk_counter}</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; padding: 5%; color: #000; background-color: #fff; }}
        p {{ text-align: justify; margin-bottom: 1.2em; text-indent: 1.5em; margin-top: 0; }}
        img {{ display: block; max-width: 100%; height: auto; margin: 1.5em auto; }}
        h1, h2 {{ text-align: center; margin-top: 1em; margin-bottom: 1.5em; }}
    </style>
</head>
<body>
    {chunk_body}
</body>
</html>"""
                    sections_content[file_name] = xhtml_template
                    manifest_items.append(f'<item id="sec_{chunk_counter}" href="{file_name}" media-type="application/xhtml+xml" />')
                    spine_items.append(f'<itemref idref="sec_{chunk_counter}" />')
                    ncx_items.append(f"""<navPoint id="navPoint_{chunk_counter}" playOrder="{chunk_counter}">
    <navLabel><text>Chapter {chunk_counter}</text></navLabel>
    <content src="{file_name}"/>
</navPoint>""")
                    
                    current_chunk_paragraphs = []
                    chunk_counter += 1
                
                current_chunk_paragraphs.append(f"<h2>{cleaned_block}</h2>")
            else:
                current_chunk_paragraphs.append(f"<p>{cleaned_block}</p>")
                
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            img_filename = f"image_{image_counter}.{image_ext}"
            images_content[img_filename] = image_bytes
            
            current_chunk_paragraphs.append(f'<div style="text-align:center; margin: 1em 0;"><img src="{img_filename}" /></div>')
            image_counter += 1

    if current_chunk_paragraphs:
        chunk_body = "\n".join(current_chunk_paragraphs)
        file_name = f"section_{chunk_counter}.xhtml"
        xhtml_template = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter {chunk_counter}</title>
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
        ncx_items.append(f"""<navPoint id="navPoint_{chunk_counter}" playOrder="{chunk_counter}">
    <navLabel><text>Chapter {chunk_counter}</text></navLabel>
    <content src="{file_name}"/>
</navPoint>""")

    doc.close()
    
    for img_name in images_content.keys():
        ext = img_name.rsplit('.', 1)[1]
        mime = "image/jpeg" if ext in ['jpg', 'jpeg'] else f"image/{ext}"
        manifest_items.append(f'<item id="{img_name}" href="{img_name}" media-type="{mime}" />')

    manifest_items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />')
    
    content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>{title_name}</dc:title>
        <dc:language>en</dc:language>
        <dc:identifier id="bookid">urn:uuid:{abs(hash(title_name))}</dc:identifier>
    </metadata>
    <manifest>
        {"\n    ".join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {"\n    ".join(spine_items)}
    </spine>
</package>"""

    toc_ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="urn:uuid:{abs(hash(title_name))}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{title_name}</text></docTitle>
    <navMap>
        {"\n".join(ncx_items)}
    </navMap>
</ncx>"""

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as epub:
        epub.writestr('mimetype', 'application/epub+zip')
        epub.writestr('META-INF/container.xml', """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>""")
        epub.writestr('OEBPS/content.opf', content_opf)
        epub.writestr('OEBPS/toc.ncx', toc_ncx)
        for f_name, f_body in sections_content.items():
            epub.writestr(f"OEBPS/{f_name}", f_body)
        for img_name, img_bytes in images_content.items():
            epub.writestr(f"OEBPS/{img_name}", img_bytes)
            
    return output_path

def convert_docx_to_txt(docx_path, output_path):
    doc = docx.Document(docx_path)
    text = [para.text for para in doc.paragraphs]
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(text))
    return output_path

def process_eink_image(image_path, output_path, target_size=(1404, 1872)):
    """Resizes proportionally and pads with white for screen compatibility."""
    with Image.open(image_path) as img:
        img = img.convert("L")
        padded_img = ImageOps.pad(img, target_size, method=Image.Resampling.LANCZOS, color=255)
        final_img = padded_img.convert("RGB")
        final_img.save(output_path, "JPEG", quality=95)
    return output_path