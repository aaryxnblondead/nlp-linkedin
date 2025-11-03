import sys
import os
from dotenv import load_dotenv

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

# Test files
test_files = [
    r"real resumes\Abdul Rahman.Khan_CV.pdf",
    r"real resumes\Anne Mariya_CV.pdf",
]

from app.services.generation import generate

for fpath in test_files:
    full_path = os.path.join(project_root, fpath)
    print(f"\n{'='*60}")
    print(f"Testing: {os.path.basename(fpath)}")
    print('='*60)
    
    text = read_file_content(full_path)
    snippet = "\n".join((text or "").splitlines()[:15])
    
    print("\n--- First 15 lines ---")
    print(snippet)
    
    print("\n--- LLM Request ---")
    prompt = (
        "Extract the full name from this resume text. Return ONLY the name, nothing else.\n\n"
        "Examples:\n"
        "- 'Abdul Rahman Khan' → Abdul Rahman Khan\n"
        "- 'Anne Mariya V V' → Anne Mariya V V\n"
        "- 'Haidar. N. Mujawar' → Haidar N Mujawar\n\n"
        "Resume text:\n" + snippet +
        "\n\nFull name:"
    )
    
    response = generate(prompt, [], max_new_tokens=32)
    
    print(f"\n--- LLM Response (raw) ---")
    print(repr(response))
    
    print(f"\n--- LLM Response (cleaned) ---")
    import re
    if response:
        ans = response.strip().splitlines()[0].strip()
        ans = re.sub(r'\.+', '.', ans)
        ans = re.sub(r'\s*\.\s*', '. ', ans)
        ans = re.sub(r'\s+', ' ', ans).strip()
        ans = ans.strip('.,;:')
        print(ans)
        print(f"Tokens: {ans.split()}")
        print(f"Token count: {len([t for t in ans.split() if t])}")
    else:
        print("(empty)")
