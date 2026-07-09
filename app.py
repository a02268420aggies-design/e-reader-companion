import os
from flask import Flask, render_template, request, send_file, redirect
from werkzeug.utils import secure_filename
# Import our unified conversion processors from formatters.py
from formatters import convert_pdf_to_epub, convert_docx_to_txt, process_eink_image

app = Flask(__name__)
app.secret_key = "super_secret_key_for_flash_messages"

# Serverless environments like Vercel require files to be processed in the writable /tmp partition
UPLOAD_FOLDER = '/tmp/uploads'
PROCESSED_FOLDER = '/tmp/processed'

ALLOWED_TEXT_EXT = {'pdf', 'doc', 'docx', 'txt'}
ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def ensure_directories():
    """Ensures ephemeral processing folders exist before running a file action."""
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
    
    ensure_directories()
    
    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)
    
    # 1. We determine extension type and assign the clean .epub mapping for PDFs
    ext = filename.rsplit('.', 1)[1].lower()
    
    if ext == 'pdf':
        output_filename = filename.rsplit('.', 1)[0] + ".epub"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        convert_pdf_to_epub(input_path, output_path)
    elif ext in ['doc', 'docx']:
        output_filename = filename.rsplit('.', 1)[0] + ".txt"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        convert_docx_to_txt(input_path, output_path)
    elif ext == 'txt':
        output_path = input_path 
    else:
        return "Unsupported format", 400

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
    
    # Converts screensavers safely to clean .jpg for the Xteink X3 OS
    output_filename = "eink_" + filename.rsplit('.', 1)[0] + ".jpg"
    output_path = os.path.join(PROCESSED_FOLDER, output_filename)
    
    process_eink_image(input_path, output_path)
    
    return send_file(output_path, as_attachment=True)