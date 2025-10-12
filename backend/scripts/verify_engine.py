"""
Print improved intelligence engine scores for a sample input.
Run:
  python backend/scripts/verify_engine.py
"""
import os
import sys
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)

from app.worker.tasks.intelligence_engine import create_structured_resume, generate_candidate_insights

RESUME = """
Alex Johnson
Staff Machine Learning Engineer
alex.j@example.com | +1 312 555 7788 | linkedin.com/in/alexj

Skills: Python, TensorFlow, PyTorch, Kubernetes, Airflow, Kafka, AWS, Terraform, Spark, Docker

Experience
Staff ML Engineer, BigTech Inc. Jan 2020 - Present
Senior ML Engineer, DataCo LLC 2016 - 2019
ML Engineer, Startup 2013 - 2016

Education
M.S. in Computer Science, Carnegie Mellon University 2011 - 2013
"""

LINKEDIN = {
  "name": "Alex Johnson",
  "posts": [
    "Proud of our team's excellent launch!",
    "Great results with Kubernetes and Spark pipelines.",
    "Helping juniors win at MLOps!"
  ],
  "activity_timestamps": ["2025-09-01","2025-09-10","2025-09-20","2025-10-01","2025-10-05"],
  "endorsed_skills": ["Kubernetes","Spark","Terraform"],
  "projects": [{"name": "Realtime ML", "tech": ["Kafka","PyTorch"], "outcome": "Reduced latency"}]
}

sr = create_structured_resume(RESUME, LINKEDIN)
ins = generate_candidate_insights(sr)
print(json.dumps({
  "rating": ins["rating"],
  "rating_label": ins["rating_label"],
  "summary": ins["summary"],
  "breakdown": ins["scoring_breakdown"],
}, indent=2))
