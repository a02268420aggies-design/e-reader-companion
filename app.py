import os
import time
import formatters 
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, jsonify

app = Flask(__name__)

# SERVERLESS COMPATIBILITY LAYER
if os.environ.get('VERCEL'):
    PROCESSED_DIR = '/tmp/processed_books'
else:
    PROCESSED_DIR = os.path.join(os.path.dirname(__file__), 'processed_books')

# Ensure the folder exists securely without breaking the read-only file system
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Separate tracking lists to keep Books and Images dynamically organized
books_db = []
images_db = []

@app.route('/')
def index():
    sort_by = request.args.get('sort', 'recent')
    
    # Render index template passing both distinct array trackers
    return render_template(
        'index.html', 
        books=books_db, 
        images=images_db, 
        current_sort=sort_by
    )

@app.route('/api/upload', methods=['POST'])
def upload_file():
    global books_db, images_db
    if 'file' not in request.files:
        return redirect(url_for('index'))
        
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
        
    if file:
        filename = file.filename
        ext = filename.lower().split('.')[-1]
        
        # 1. Temporarily save the incoming file so formatters can read it
        temp_path = os.path.join(PROCESSED_DIR, f"temp_{filename}")
        file.save(temp_path)
        
        try:
            # 2. Run your pipeline formatter!
            processed_data = formatters.process_and_save_book(temp_path, filename)
            
            # 3. Determine new output extension and filename
            if ext in ['pdf', 'epub', 'txt']:
                final_filename = filename.rsplit('.', 1)[0] + '.txt'
                final_path = os.path.join(PROCESSED_DIR, final_filename)
                
                # Save parsed text string out as a clean text file
                with open(final_path, 'w', encoding='utf-8') as f:
                    f.write(processed_data)
            else:
                # Save the PNG version for the web dashboard preview
                final_filename = filename.rsplit('.', 1)[0] + '_eink.png'
                final_path = os.path.join(PROCESSED_DIR, final_filename)
                processed_data.save(final_path, format='PNG')
                
                # Mirror a BMP version for the hardware sleep cover engine
                bmp_filename = filename.rsplit('.', 1)[0] + '_eink.bmp'
                bmp_path = os.path.join(PROCESSED_DIR, bmp_filename)
                processed_data.save(bmp_path, format='BMP')
                
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return f"Processing Error: {str(e)}", 500

        # Clean up the original temp upload file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        # 4. SORT METADATA INTO THE CORRECT DATABASE TAB
        if ext in ['pdf', 'epub', 'txt']:
            new_book = {
                "id": int(time.time()),
                "title": final_filename.rsplit('.', 1)[0].replace('_', ' '),
                "filename": final_filename,
                "size": f"{os.path.getsize(final_path) // 1024} KB",
                "type": "document"
            }
            books_db.append(new_book)
        else:
            new_image = {
                "id": int(time.time()),
                "title": final_filename.rsplit('.', 1)[0].replace('_', ' '),
                "filename": final_filename,  # FIX: Set this to final_filename (which ends in _eink.png)
                "sleep_filename": filename.rsplit('.', 1)[0] + '_eink.bmp',  # Keeps this for the e-reader
                "size": f"{os.path.getsize(final_path) // 1024} KB",
                "type": "image"
            }
            images_db.append(new_image)
        
        return redirect(url_for('index'))

@app.route('/api/delete/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    global books_db, images_db
    
    # Check if the asset to delete lives in books or images
    book_to_remove = next((b for b in books_db if b["id"] == book_id), None)
    image_to_remove = next((i for i in images_db if i["id"] == book_id), None)
    target = book_to_remove or image_to_remove
    
    if target:
        # Delete primary file (PNG or TXT)
        file_path = os.path.join(PROCESSED_DIR, target["filename"])
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # If it's an image, delete its paired BMP sleep file too
        if "sleep_filename" in target:
            bmp_path = os.path.join(PROCESSED_DIR, target["sleep_filename"])
            if os.path.exists(bmp_path):
                os.remove(bmp_path)
            
        # Filter item out of the respective database lists
        books_db = [b for b in books_db if b["id"] != book_id]
        images_db = [i for i in images_db if i["id"] != book_id]
        return jsonify({"success": True})
        
    return jsonify({"error": "Item not found"}), 404

@app.route('/download/<filename>')
def download_file(filename):
    if filename.lower().endswith('.bmp'):
        mimetype = 'image/bmp'
    elif filename.lower().endswith('.png'):
        mimetype = 'image/png'
    else:
        mimetype = None
    return send_from_directory(PROCESSED_DIR, filename, mimetype=mimetype)

@app.route('/api/device/download/<filename>', methods=['GET'])
def device_download(filename):
    if filename.lower().endswith('.bmp'):
        mimetype = 'image/bmp'
    elif filename.lower().endswith('.png'):
        mimetype = 'image/png'
    else:
        mimetype = None
    return send_from_directory(PROCESSED_DIR, filename, mimetype=mimetype)

@app.route('/api/device/sync_all', methods=['GET'])
def sync_all_books():
    # Force the device images list payload to supply the BMP file targets instead of PNGs
    device_images = []
    for img in images_db:
        device_images.append({
            "id": img["id"],
            "title": img["title"],
            "filename": img.get("sleep_filename", img["filename"]),
            "size": img["size"],
            "type": "image"
        })

    return jsonify({
        "books": books_db,
        "images": device_images
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)