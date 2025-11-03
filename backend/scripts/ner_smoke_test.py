import sys
import os
import json
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv
import time

# Load .env file from the project root, which is two levels up from this script's directory.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))

# Ensure the 'backend' directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ner import extract_resume_entities
from app.services.generation import generate

# --- Configuration ---
RESUME_DIR = os.path.join(project_root, 'real resumes')
REPORT_FILE = os.path.join(project_root, "ner_accuracy_report.txt")

def get_resume_files(directory: str) -> List[str]:
    """Get a list of resume file paths from the specified directory."""
    files = []
    if not os.path.isdir(directory):
        print(f"Error: Directory not found at '{directory}'")
        return files
    for filename in os.listdir(directory):
        # Add more extensions as needed
        if filename.lower().endswith(('.txt', '.pdf', '.docx')):
            files.append(os.path.join(directory, filename))
    return files

def read_file_content(file_path: str) -> str:
    """Read content from a file (supports .txt, basic .pdf/.docx with PyMuPDF/python-docx)."""
    if file_path.lower().endswith('.pdf'):
        try:
            import fitz  # PyMuPDF
            with fitz.open(file_path) as doc:
                # Ensure each page's text is treated as a string
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
    else:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Error reading TXT: {e}"

def generate_ground_truth(resume_text: str) -> Dict[str, Any]:
    """Use an AI model to generate the ground truth entities for a resume."""
    prompt = f"""
    You are an expert HR assistant. Analyze the following resume text and extract the key entities.
    Return a single, compact JSON object with the following keys: "name", "email", "skills", "titles", "organizations", "education", "experience".
    - "skills", "titles", "organizations" should be lists of strings.
    - "education" and "experience" should be lists of objects with relevant details.
    - If a field is not found, provide an empty list or null.

    Resume Text:
    ---
    {resume_text[:4000]}
    ---

    JSON Output:
    """
    try:
        # Increase max_new_tokens to ensure the full JSON can be generated.
        response = generate(prompt, [], max_new_tokens=3072)
        
        # Use regex to find the JSON block, handling optional markdown fences
        import re
        json_str = ""
        match = re.search(r'```(json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if match:
            json_str = match.group(2)
        else:
            # Fallback to finding the first '{' and last '}'
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response[start:end+1]
            else:
                print(f"  - Warning: No JSON object found in AI response. Response was: {response}")
                return {}

        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"  - Warning: Could not parse ground truth from AI. Error: {e}")
        # Temporarily print the faulty string for debugging
        if 'json_str' in locals():
            print(f"  - Faulty JSON string: {json_str}")
        return {}
    except Exception as e:
        print(f"  - Warning: An unexpected error occurred during AI generation: {e}")
        return {}

def calculate_list_metrics(predicted: List[str], truth: List[str]) -> Tuple[float, float, float]:
    """Calculates Precision, Recall, and F1-Score for lists of strings."""
    if not isinstance(predicted, list) or not isinstance(truth, list):
        return 0.0, 0.0, 0.0

    pred_set = {str(p).lower().strip() for p in predicted}
    truth_set = {str(t).lower().strip() for t in truth}

    if not truth_set and not pred_set:
        return 1.0, 1.0, 1.0 # Both empty is a perfect match

    true_positives = len(pred_set.intersection(truth_set))
    
    precision = true_positives / len(pred_set) if pred_set else 0.0
    recall = true_positives / len(truth_set) if truth_set else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return precision, recall, f1

def main():
    """Main function to run the NER smoke test and generate a report."""
    # Ensure required packages for file reading are installed
    try:
        import fitz
        import docx
    except ImportError:
        print("Error: Missing required packages. Please run:")
        print("pip install PyMuPDF python-docx python-dotenv")
        return

    resume_files = get_resume_files(RESUME_DIR)
    if not resume_files:
        print("No resume files found. Exiting.")
        return

    total_scores = {
        "name": {"correct": 0, "total": 0},
        "email": {"correct": 0, "total": 0},
        "skills": {"precision": [], "recall": [], "f1": []},
        "titles": {"precision": [], "recall": [], "f1": []},
    }

    report_lines = []

    for i, file_path in enumerate(resume_files[:5], 1):
        print(f"--- Processing Resume {i}/{len(resume_files[:5])}: {os.path.basename(file_path)} ---")
        report_lines.append(f"\n---=== {os.path.basename(file_path)} ===---")

        content = read_file_content(file_path)
        if content.startswith("Error"):
            print(f"  - Skipping due to read error: {content}")
            report_lines.append(f"SKIPPED: {content}")
            continue

        # 1. Generate ground truth using AI
        print("  - Generating ground truth from AI...")
        ground_truth = generate_ground_truth(content)
        if not ground_truth:
            report_lines.append("SKIPPED: Could not generate ground truth.")
            continue

        # 2. Run our NER system
        print("  - Running local NER extraction...")
        predicted = extract_resume_entities(content)

        # 3. Compare and score
        # Name - normalize periods in initials for fair comparison
        import re
        gt_name = (ground_truth.get("name") or "").lower().strip()
        pred_name = (predicted.get("name") or "").lower().strip()
        # Remove all periods for comparison (handles both "n." and "haidar." cases)
        gt_name_normalized = gt_name.replace('.', '').strip()
        pred_name_normalized = pred_name.replace('.', '').strip()
        # Also normalize multiple spaces
        gt_name_normalized = re.sub(r'\s+', ' ', gt_name_normalized)
        pred_name_normalized = re.sub(r'\s+', ' ', pred_name_normalized)
        if gt_name:
            total_scores["name"]["total"] += 1
            if gt_name_normalized == pred_name_normalized:
                total_scores["name"]["correct"] += 1
            report_lines.append(f"Name Accuracy: {'PASS' if gt_name_normalized == pred_name_normalized else 'FAIL'}")
            report_lines.append(f"  - Truth: {gt_name}")
            report_lines.append(f"  - Pred:  {pred_name}")

        # Email
        gt_email = (ground_truth.get("email") or "").lower().strip()
        pred_email = (predicted.get("email") or "").lower().strip()
        if gt_email:
            total_scores["email"]["total"] += 1
            if gt_email == pred_email:
                total_scores["email"]["correct"] += 1
            report_lines.append(f"Email Accuracy: {'PASS' if gt_email == pred_email else 'FAIL'}")
            report_lines.append(f"  - Truth: {gt_email}")
            report_lines.append(f"  - Pred:  {pred_email}")

        # Skills & Titles (list-based metrics)
        for field in ["skills", "titles"]:
            p, r, f1 = calculate_list_metrics(predicted.get(field, []), ground_truth.get(field, []))
            total_scores[field]["precision"].append(p)
            total_scores[field]["recall"].append(r)
            total_scores[field]["f1"].append(f1)
            report_lines.append(f"{field.capitalize()} Metrics: P={p:.2f}, R={r:.2f}, F1={f1:.2f}")
            report_lines.append(f"  - Truth: {ground_truth.get(field, [])}")
            report_lines.append(f"  - Pred:  {predicted.get(field, [])}")

        time.sleep(35)  # To avoid hitting rate limits

    # 4. Generate final report
    print("\n--- Generating Final Report ---")
    summary_header = "---=== AGGREGATE NER ACCURACY REPORT ===---"
    
    final_report = [summary_header]
    
    # Scalar fields (Name, Email)
    for field in ["name", "email"]:
        correct = total_scores[field]["correct"]
        total = total_scores[field]["total"]
        acc = (correct / total) * 100 if total > 0 else 0
        final_report.append(f"\nTotal {field.capitalize()} Accuracy: {acc:.2f}% ({correct}/{total})")

    # List fields (Skills, Titles)
    for field in ["skills", "titles"]:
        prec_list = total_scores[field]["precision"]
        rec_list = total_scores[field]["recall"]
        f1_list = total_scores[field]["f1"]
        
        avg_p = (sum(prec_list) / len(prec_list)) if prec_list else 0
        avg_r = (sum(rec_list) / len(rec_list)) if rec_list else 0
        avg_f1 = (sum(f1_list) / len(f1_list)) if f1_list else 0
        
        final_report.append(f"\nAverage {field.capitalize()} Metrics:")
        final_report.append(f"  - Precision: {avg_p:.2f}")
        final_report.append(f"  - Recall:    {avg_r:.2f}")
        final_report.append(f"  - F1-Score:  {avg_f1:.2f}")

    final_report.append("\n\n---=== DETAILED PER-RESUME LOG ===---")
    final_report.extend(report_lines)

    report_content = "\n".join(final_report)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"\nReport saved to '{REPORT_FILE}'")


if __name__ == "__main__":
    main()