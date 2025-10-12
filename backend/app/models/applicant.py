from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime
import enum

Base = declarative_base()

class Applicant(Base):
    __tablename__ = 'applicants'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # link to users.id
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    resume_path = Column(String, nullable=False)
    linkedin_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    class Status(enum.Enum):
        submitted = "submitted"
        processing = "processing"
        processed = "processed"
        failed = "failed"

    status = Column(Enum(Status), nullable=True, default=Status.submitted)
    resume = relationship('Resume', back_populates='applicant', uselist=False)
    linkedin = relationship('LinkedInProfile', back_populates='applicant', uselist=False)
    insights = relationship('Insights', back_populates='applicant', uselist=False)

class Resume(Base):
    __tablename__ = 'resumes'
    id = Column(Integer, primary_key=True, index=True)
    applicant_id = Column(Integer, ForeignKey('applicants.id'))
    raw_text = Column(String, nullable=True)
    structured_data = Column(JSON, nullable=True)
    applicant = relationship('Applicant', back_populates='resume')

class LinkedInProfile(Base):
    __tablename__ = 'linkedin_profiles'
    id = Column(Integer, primary_key=True, index=True)
    applicant_id = Column(Integer, ForeignKey('applicants.id'))
    profile_data = Column(JSON, nullable=True)
    applicant = relationship('Applicant', back_populates='linkedin')

class Insights(Base):
    __tablename__ = 'insights'
    id = Column(Integer, primary_key=True, index=True)
    applicant_id = Column(Integer, ForeignKey('applicants.id'))
    rating = Column(Integer, nullable=True)
    summary = Column(String, nullable=True)
    # New fields per MVP
    sentiment_score = Column(Float, nullable=True)
    activity_score = Column(Float, nullable=True)
    top_endorsed_skills = Column(JSON, nullable=True)
    projects = Column(JSON, nullable=True)
    experience_years = Column(Integer, nullable=True)
    consistency_flags = Column(JSON, nullable=True)
    scoring_breakdown = Column(JSON, nullable=True)
    applicant = relationship('Applicant', back_populates='insights')
