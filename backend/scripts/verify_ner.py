"""
Quick smoke test for NER service. Run with your Python env active:
  python backend/scripts/verify_ner.py
"""
import os
import sys
import json

# Ensure project import path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)

sample = """
John A. Doe
Senior Software Engineer
john.doe@example.com | +1 (415) 555-1234 | https://www.linkedin.com/in/johndoe

Skills: Python, FastAPI, Docker, AWS, Kubernetes, PostgreSQL, Pandas

Experience
Senior Software Engineer, Example Inc. Jan 2020 - Present
Software Engineer, Acme LLC 2017 - 2019

Education
B.Tech in Computer Science, Great State University 2013 - 2017
"""

from app.services.ner import extract_resume_entities

ents = extract_resume_entities(sample)
print(json.dumps(ents, indent=2))
