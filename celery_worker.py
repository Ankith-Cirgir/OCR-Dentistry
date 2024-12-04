# celery_worker.py

from celery import Celery
import os
import logging
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def make_celery():
    # Initialize Celery with broker and backend from environment variables or default to Redis
    celery = Celery(
        'ocr_app',
        broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    )
    celery.conf.update()
    return celery

celery = make_celery()

@celery.task(bind=True)
def ocr_task(self, pdf_path, output_path):
    try:
        logger.info(f"Starting OCR task for {pdf_path}")
        
        # Convert PDF to images
        pages = convert_from_path(pdf_path, dpi=300)
        logger.info(f"Converted PDF to {len(pages)} image(s)")

        ocr_text = ""
        for page_number, page in enumerate(pages, start=1):
            logger.info(f"Performing OCR on page {page_number}")
            text = pytesseract.image_to_string(page)
            ocr_text += f"--- Page {page_number} ---\n{text}\n\n"

        # Save OCR result to output path
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ocr_text)

        logger.info(f"OCR task completed for {pdf_path}, output saved to {output_path}")
        return {"status": "Completed", "output_path": output_path}
    except Exception as e:
        logger.error(f"OCR task failed for {pdf_path}: {e}")
        self.update_state(state='FAILURE', meta={'exc_message': str(e)})
        raise e