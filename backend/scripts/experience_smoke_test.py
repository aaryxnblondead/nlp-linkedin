from app.worker.tasks.intelligence_engine import estimate_experience_years

structured = {
  "experience": [
    {"title":"Software Engineer","start":"Jan 2018","end":"Dec 2020"},
    {"title":"Senior Software Engineer","start":"Jan 2021","end":"Present"},
    {"title":"Intern","start":"Jun 2017","end":"Dec 2017"},
    {"title":"Developer","start":"2019","end":"2022"},
  ]
}
print(estimate_experience_years(structured))
