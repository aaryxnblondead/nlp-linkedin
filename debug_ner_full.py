import sys
import os
import logging
from dotenv import load_dotenv

# Configure logging to show INFO level
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Load .env file from the project root
project_root = os.path.abspath(os.path.dirname(__file__))
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))

# Ensure the 'backend' directory is in the Python path
sys.path.insert(0, os.path.join(project_root, 'backend'))

# Read resume files
def read_file_content(file_path: str) -> str:
    """Read content from a file (supports .txt, basic .pdf/.docx with PyMuPDF/python-docx)."""
    if file_path.lower().endswith('.pdf'):
        try:
            import fitz  # PyMuPDF
            with fitz.open(file_path) as doc:
                return "".join(str(page.get_text()) for page in doc)
        except Exception as e:
            return f"Error reading PDF: {e}"
    elif file_path.lower().endswith('.docx'):
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            return f"Error reading DOCX: {e}"

# Test with Abdul Rahman
test_file = r"real resumes\Abdul Rahman.Khan_CV.pdf"
full_path = os.path.join(project_root, test_file)

print(f"\n{'='*60}")
print(f"Testing NER extraction: {os.path.basename(test_file)}")
print('='*60)

text = read_file_content(full_path)

from app.services.ner import extract_resume_entities

print("\n--- Calling extract_resume_entities ---\n")
result = extract_resume_entities(text)

print("\n--- Results ---")
print(f"Name: {result.get('name')!r}")
print(f"Email: {result.get('email')!r}")
