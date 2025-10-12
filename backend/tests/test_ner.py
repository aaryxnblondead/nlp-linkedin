import os
import sys

# Ensure project import path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)

from app.services.ner import extract_resume_entities

SAMPLE_1 = """
Jane Smith
Data Scientist
jane.smith@sample.co | (212) 555-9876 | https://linkedin.com/in/janes

Skills: Python, pandas, scikit-learn, AWS, Docker

Experience
Data Scientist, CoolTech Inc. Feb 2021 - Present
Machine Learning Engineer, DataWorks LLC 2018 - 2021

Education
M.S. in Computer Science, Stanford University 2016 - 2018
"""

SAMPLE_2 = """
Rahul Kumar
Senior DevOps Engineer | AWS Certified
Email: rahul.kumar@example.com | Phone: +91 98765 43210 | LinkedIn: linkedin.com/in/rahulk

Skills
Kubernetes | Terraform | Jenkins | Prometheus | Grafana | Python

Experience
Senior DevOps Engineer - ACME Ltd 2020 - Present
DevOps Engineer - GlobalSoft 2017 - 2020

Education
B.Tech in Information Technology, IIT Delhi 2013 - 2017
"""

def test_extract_basic_contacts():
    ents = extract_resume_entities(SAMPLE_1)
    assert ents["name"] and "Jane" in ents["name"]
    assert ents["email"] == "jane.smith@sample.co"
    assert "aws" in [s.lower() for s in ents["skills"]]
    assert "docker" in [s.lower() for s in ents["skills"]]
    assert any("Stanford" in (e.get("institution") or "") for e in ents["education"])


def test_extract_phone_and_linkedin():
    ents = extract_resume_entities(SAMPLE_1)
    assert ents["phone"] and "212" in ents["phone"]
    assert "linkedin.com/in/janes" in ents["linkedin"]


def test_titles_and_experience():
    ents = extract_resume_entities(SAMPLE_1)
    titles = [t.lower() for t in ents["titles"]]
    assert "data scientist" in titles
    assert any((exp.get("title") or "").lower().startswith("data scientist") for exp in ents["experience"])


def test_india_phone_and_gpe():
    ents = extract_resume_entities(SAMPLE_2)
    assert ents["phone"]
    assert "98765" in ents["phone"]
    assert any("IIT" in (e.get("institution") or "") for e in ents["education"])
