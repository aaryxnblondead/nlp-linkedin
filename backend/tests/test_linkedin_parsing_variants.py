from app.worker.tasks.intelligence_engine import generate_candidate_insights


def test_generate_insights_role_profiles():
    sr = {
        "skills": ["python", "pytorch", "kubernetes", "airflow"],
        "titles": ["Senior Machine Learning Engineer"],
        "education": [{"degree": "M.S Computer Science", "institution": "IIT Delhi"}],
        "experience": [
            {"start": "Jan 2018", "end": "Present", "title": "Senior ML Engineer"}
        ],
        "raw_text": "",
        "linkedin": {"posts": ["Great work"], "activity_timestamps": ["2024-01-01", "2024-02-01"]},
    }
    res_default = generate_candidate_insights(sr)
    res_ml = generate_candidate_insights(sr, role="ml engineer")
    assert res_ml["rating"] >= res_default["rating"] - 5


def test_linkedin_shape_variants():
    # Missing posts/activity should not crash and should yield 0 activity
    sr = {"skills": ["python"], "titles": ["Engineer"], "education": [], "experience": [], "raw_text": "", "linkedin": {}}
    res = generate_candidate_insights(sr)
    assert res["activity_score"] == 0.0
    # Posts present but timestamps missing still ok
    sr2 = {"skills": ["python"], "titles": ["Engineer"], "education": [], "experience": [], "raw_text": "", "linkedin": {"posts": ["Good day!"]}}
    res2 = generate_candidate_insights(sr2)
    assert "rating" in res2
