# ocr_flask.py

from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import os
from celery_worker import ocr_task, celery  # Import tasks and celery app
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure upload and output folders
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Allowed extensions
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Check if a file was uploaded
        if "pdf_file" not in request.files or request.files["pdf_file"].filename == "":
            return jsonify({"error": "No PDF file uploaded."}), 400

        pdf_file = request.files["pdf_file"]
        output_name = request.form.get("output_name", "output").strip()

        # Validate output_name to prevent security issues
        if not output_name:
            output_name = "output"

        # Validate file type
        if not allowed_file(pdf_file.filename):
            return jsonify({"error": "Invalid file type. Only PDF files are allowed."}), 400

        # Secure the filename
        filename = secure_filename(pdf_file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_file.save(pdf_path)

        # Output file path
        output_filename = f"{output_name}.txt"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        # Enqueue OCR task
        try:
            task = ocr_task.delay(str(pdf_path), str(output_path))
            logger.info(f"Enqueued OCR task with ID: {task.id}")
            return jsonify({"task_id": task.id}), 202
        except Exception as e:
            logger.error(f"Failed to enqueue OCR task: {e}")
            return jsonify({"error": str(e)}), 500

    return render_template("index.html")

@app.route("/task_status/<task_id>")
def task_status(task_id):
    task = celery.AsyncResult(task_id)
    return jsonify({
        "task_id": task.id,
        "state": task.state,
        "result": task.result if task.state == 'SUCCESS' else None
    }), 200

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        # Security Check: Ensure the filename is secure
        filename = secure_filename(filename)
        logger.info(f"Download requested for file: {filename}")
        
        # Verify the file exists in the outputs directory
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        print(f"File path: {file_path}")
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {filename}")
            return jsonify({"error": "Resource Not Found"}), 404
        
        # Correct usage of send_from_directory with 'directory' and 'filename'
        return send_from_directory(directory=app.config['OUTPUT_FOLDER'], path=filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error in download_file route: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Custom error handlers to ensure JSON responses
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal Server Error"}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Resource Not Found"}), 404

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({"error": "Bad Request"}), 400

if __name__ == "__main__":
    app.run(debug=True, port=8080)  # Ensure running on port 5000