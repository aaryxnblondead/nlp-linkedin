from app.services.ner import extract_resume_entities

samples = []
samples.append("John Doe\nSoftware Engineer\nEmail: john.doe@example.com\nPhone: +1 555 123 4567")
samples.append("Team Lead\nEmail: john dot doe at example dot com")
samples.append("DI Developer\nemail john . doe @ example . co . in")
samples.append("Actimize IFM\nMail: jane_doe at gmail dot com")
samples.append("Name: Rahul Sharma\nProfile\nrahul at the rate outlook dot com")

for i, s in enumerate(samples, 1):
    e = extract_resume_entities(s)
    print(f"--- Sample {i} ---")
    print("Name:", e.get("name"))
    print("Email:", e.get("email"))
    print("Titles:", e.get("titles"))
    print()