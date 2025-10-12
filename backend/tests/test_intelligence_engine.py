import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, PROJECT_ROOT)

from app.worker.tasks.intelligence_engine import create_structured_resume, generate_candidate_insights

STRONG_SKILLS_LOW_SENTIMENT = {
    "resume": """
    Sam Expert
    Principal Software Engineer
    Email: sam@example.com
    Skills: Kubernetes, Terraform, Spark, Kafka, AWS, GCP, Airflow, PyTorch, TensorFlow, ElasticSearch
    Experience
    Principal Software Engineer, BigCo 2016 - Present
    """,
    "linkedin": {
        "name": "Sam Expert",
        "posts": ["I hate how bad the latest release was.", "Poor quality in the new service.", "Fail after fail."],
        "activity_timestamps": ["2025-08-01", "2025-08-10"]
    }
}

INTERN_HIGH_ACTIVITY = {
    "resume": """
    Alex Intern
    Software Engineering Intern
    Email: alex@example.com
    Skills: Python, React
    Experience
    Software Engineering Intern, Startup 2025 - Present
    """,
    "linkedin": {
        "name": "Alex Intern",
        "posts": ["Learning a lot!", "Great mentorship!", "Good sprint so far!"],
        "activity_timestamps": ["2025-09-01","2025-09-03","2025-09-05","2025-09-07","2025-09-09","2025-09-11","2025-09-13","2025-09-15","2025-09-17","2025-09-19"]
    }
}

def test_strong_skills_low_sentiment():
    sr = create_structured_resume(STRONG_SKILLS_LOW_SENTIMENT["resume"], STRONG_SKILLS_LOW_SENTIMENT["linkedin"])
    ins = generate_candidate_insights(sr)
    # Expect solid rating despite negative sentiment; ensure rating not collapsed
    assert ins["rating"] >= 60
    assert ins["sentiment_score"] < 0


def test_intern_high_activity():
    sr = create_structured_resume(INTERN_HIGH_ACTIVITY["resume"], INTERN_HIGH_ACTIVITY["linkedin"])
    ins = generate_candidate_insights(sr)
    # Expect modest rating due to low seniority/experience even with high activity
    assert ins["rating"] < 70
    assert ins["activity_score"] >= 1.0 or ins["activity_score"] > 0.8
