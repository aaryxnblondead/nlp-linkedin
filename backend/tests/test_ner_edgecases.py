import pytest
from app.services.ner import extract_resume_entities


def test_linkedin_variants():
    text = (
        "LinkedIn: https://www.linkedin.com/in/john-doe-12345\n"
        "Also profile: http://linkedin.com/in/Jane_Doe%2Fprofile\n"
    )
    ent = extract_resume_entities(text)
    assert ent["linkedin"].startswith("http")
    assert "linkedin.com" in ent["linkedin"].lower()


ess_text = """
John Doe
Email: john@example.com
Phone: +91 98765 43210 ext 123
Experience
Senior Software Engineer at Example Inc. Jan 2019 - Present
"""

def test_phone_extension_and_experience_title():
    ent = extract_resume_entities(ess_text)
    assert "987" in (ent["phone"] or "")
    titles = [t.lower() for t in ent.get("titles", [])]
    assert any("senior software engineer" in t for t in titles)


def test_org_skill_bleed_reduction():
    text = (
        "Skills: Kubernetes, Terraform, Python\n"
        "Experience: Python Developer at Data Inc. 2020-2022\n"
        "Location: Remote\n"
    )
    ent = extract_resume_entities(text)
    orgs = [o.lower() for o in ent.get("organizations", [])]
    # Ensure skill words like Python are not misclassified as ORG
    assert not any(o == "python" for o in orgs)


def test_title_detection_no_section_header():
    text = "Worked as a Staff Software Engineer, Google (2018-2021) leading infra."
    ent = extract_resume_entities(text)
    titles = [t.lower() for t in ent.get("titles", [])]
    assert any("staff software engineer" in t for t in titles)
