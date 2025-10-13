from app.worker.tasks.data_ingestion import process_resume_file
print('PDF len:', len(process_resume_file('..\\real resumes\\Sushma Singh_Resume.pdf')))
print('DOCX len:', len(process_resume_file('..\\real resumes\\SaikatCV.docx')))
print('DOC mislabeled len:', len(process_resume_file('..\\real resumes\\Lakshmi Narayana_CV.doc')))