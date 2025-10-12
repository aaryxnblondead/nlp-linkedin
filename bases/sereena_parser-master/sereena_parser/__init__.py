"""
Sereena Parser - Production-ready resume parser with multi-threading support

A high-performance resume parser that extracts structured information from PDF and DOCX files
with advanced NLP capabilities and multi-threading optimization.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .main import (
    ResumeParser,
    TextExtractor,
    EntityExtractor,
    PersonalInfo,
    Education,
    Experience,
    ResumeData,
)

__all__ = [
    "ResumeParser",
    "TextExtractor", 
    "EntityExtractor",
    "PersonalInfo",
    "Education", 
    "Experience",
    "ResumeData",
]