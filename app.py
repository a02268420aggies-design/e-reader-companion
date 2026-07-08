import os
from flask import Flask, request, render_template, redirect, url_for, jsonify, send_from_directory
from formatters import process_and_save_book
from PIL import Image

app = Flask(__name__)
UPLOAD_FOLDER = 'processed_books'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Starting with a dynamic list that maps the files currently in the directory
books_db = [
    {"id": 1, "title": "The Hobbit", "filename": "the_hobbit.txt", "status": "synced"},
    {"id": 2, "title": "The Design Of Everyday Things", "filename": "the_design_of_everyday_things.txt", "status": "pending_sync"}
]

@app.route('/')
def index():
    # Grab a sorting preference from the URL (default to 'recent')
    sort_by = request.args.get('sort', 'recent')
    
    if sort_by == 'alpha':
        # Sort by book title alphabetically
        display_books = sorted(books_db, key=lambda x: x['title'].lower())
    else:
        # Default: Sort by ID descending (Most recent uploads show first)
        display_books = sorted(books_db, key=lambda x: x['id'], reverse=True)
        
    return render_template('index.html', books=display_books, current_sort=sort_by)

@app.route('/api/upload', methods=['POST'])
def upload_book():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))

    if file:
        filename = file.filename
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            ext = filename.lower().split('.')[-1]
            base_name = filename.rsplit('.', 1)[0]
            
            # 1. Run through our processing engine
            processed_output = process_and_save_book(temp_path, filename)
            
            if ext in ['jpg', 'jpeg', 'png', 'bmp']:
                # Save as a clean dithered BMP/PNG for the hardware reader
                output_filename = f"{base_name}_dithered.png"
                output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
                processed_output.save(output_path)
                display_title = f"🖼️ Image: {base_name.replace('_', ' ').replace('-', ' ').title()}"
            else:
                # Save as plain text
                output_filename = f"{base_name}.txt"
                output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(processed_output)
                display_title = base_name.replace('_', ' ').replace('-', ' ').title()

            # Remove temporary source file if it isn't the final format
            if filename != output_filename:
                os.remove(temp_path)
                
            next_id = max([b['id'] for b in books_db]) + 1 if books_db else 1
            
            new_book = {
                "id": next_id,
                "title": display_title,
                "filename": output_filename,
                "status": "pending_sync"
            }
            books_db.append(new_book)
            
        except Exception as e:
            print(f"Error processing upload: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    return redirect(url_for('index'))

# --- NEW: ROUTE TO DELETE A BOOK ---
@app.route('/api/delete/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    """Deletes the book from memory and wipes its physical .txt file from the hard drive."""
    global books_db
    book_to_remove = next((b for b in books_db if b["id"] == book_id), None)
    
    if book_to_remove:
        # 1. Remove its file from the processed_books folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], book_to_remove["filename"])
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # 2. Remove it from our runtime database list
        books_db = [b for b in books_db if b["id"] != book_id]
        return jsonify({"success": True})
        
    return jsonify({"error": "Book not found"}), 404

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/api/device/sync_all', methods=['GET'])
def sync_all_books():
    return jsonify({"books": books_db})

@app.route('/api/device/download/<filename>', methods=['GET'])
def device_download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)