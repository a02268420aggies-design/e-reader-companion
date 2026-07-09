import os
from flask import Flask, render_template, request, send_file, redirect
from werkzeug.utils import secure_filename
from formatters import convert_pdf_to_txt, convert_docx_to_txt, process_eink_image

app = Flask(__name__)
app.secret_key = "super_secret_key_for_flash_messages"

# Use /tmp for serverless runtime
UPLOAD_FOLDER = '/tmp/uploads'
PROCESSED_FOLDER = '/tmp/processed'

ALLOWED_TEXT_EXT = {'pdf', 'doc', 'docx', 'txt'}
ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def ensure_directories():
    """Helper to ensure folders exist only when a request happens."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload-text', methods=['POST'])
def upload_text():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename, ALLOWED_TEXT_EXT):
        return "Invalid file type", 400
    
    # Create folders safely right before use
    ensure_directories()
    
    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)
    
    output_filename = filename.rsplit('.', 1)[0] + ".txt"
    output_path = os.path.join(PROCESSED_FOLDER, output_filename)
    
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        convert_pdf_to_txt(input_path, output_path)
    elif ext in ['doc', 'docx']:
        convert_docx_to_txt(input_path, output_path)
    elif ext == 'txt':
        output_path = input_path 

    return send_file(output_path, as_attachment=True)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename, ALLOWED_IMG_EXT):
        return "Invalid image type", 400
    
    ensure_directories()
    
    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)
    
    # FIX: Changed extension from .png to .jpg
    output_filename = "eink_" + filename.rsplit('.', 1)[0] + ".jpg"
    output_path = os.path.join(PROCESSED_FOLDER, output_filename)
    
    process_eink_image(input_path, output_path)
    
    return send_file(output_path, as_attachment=True)