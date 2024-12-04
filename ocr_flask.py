from flask import Flask, request, render_template, send_file, redirect, url_for
from pathlib import Path
from tempfile import TemporaryDirectory
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os

# Configure Flask
app = Flask(__name__)

# Configure pytesseract and poppler paths for Windows
if os.name == "nt":  # Check if the OS is Windows
    pytesseract.pytesseract.tesseract_cmd = r"C:\Users\acirg682\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    poppler_path = r"C:\Users\acirg682\OneDrive - Meharry Medical College\Desktop\OCR\poppler-24.08.0\Library\bin"
else:
    poppler_path = None  # Assume Poppler is installed system-wide on non-Windows systems

# Define the upload and output folders
UPLOAD_FOLDER = Path("uploads")
OUTPUT_FOLDER = Path("outputs")
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Check if a file was uploaded
        if "pdf_file" not in request.files or request.files["pdf_file"].filename == "":
            return "No PDF file uploaded.", 400

        pdf_file = request.files["pdf_file"]
        output_name = request.form.get("output_name", "output.txt")

        # Save the uploaded file
        pdf_path = UPLOAD_FOLDER / pdf_file.filename
        pdf_file.save(pdf_path)

	#OUTPUT_FOLDER.mkdir(exist_ok=True)
        # Output file path
        output_path = OUTPUT_FOLDER / f"{output_name}.txt"  # Ensure it has a .txt extension

        # Process the PDF
        try:
            ocr_pdf_to_text(pdf_path, output_path)
            return redirect(url_for("download", output_name=output_name))
        except Exception as e:
            return f"An error occurred: {e}", 500

    return render_template("index.html")

@app.route("/download/<output_name>")
def download(output_name):
    # Construct the output file path
    output_name += ".txt"
    output_path = OUTPUT_FOLDER / output_name

    # Debugging: Print the output path
    print(f"Download request for: {output_path}")

    # Check if the file exists
    if not output_path.exists():
        print(f"File not found: {output_path}")
        return "Output file not found.", 404

    # Send the file to the user
    try:
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        print(f"Error sending file: {e}")
        return f"An error occurred while sending the file: {e}", 500

def ocr_pdf_to_text(pdf_path, output_path):
    """Converts a PDF file to text using OCR and saves it to the output file."""
    with TemporaryDirectory() as tempdir:
        tempdir_path = Path(tempdir)

        # Convert PDF to images
        pdf_pages = convert_from_path(str(pdf_path), 500, poppler_path=poppler_path)

        image_file_list = []

        for page_num, page in enumerate(pdf_pages, start=1):
            image_path = tempdir_path / f"page_{page_num:03}.jpg"
            page.save(image_path, "JPEG")
            image_file_list.append(image_path)

        # Perform OCR
        with open(output_path, "w", encoding="utf-8") as output_file:
            for image_file in image_file_list:
                text = pytesseract.image_to_string(Image.open(image_file))
                text = text.replace("-\n", "")  # Remove hyphenated line breaks
                output_file.write(text)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    path = UPLOAD_FOLDER / filename
    return send_file(path)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
