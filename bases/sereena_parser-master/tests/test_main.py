import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add the parent directory to sys.path to import sereena_parser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sereena_parser.main import (
    ResumeParser, 
    TextExtractor, 
    EntityExtractor,
    PersonalInfo,
    Education,
    Experience,
    ResumeData
)


class TestTextExtractor:
    """Test cases for TextExtractor class"""
    
    def test_extract_from_docx_mock(self):
        """Test DOCX extraction with mocked Document"""
        with patch('sereena_parser.main.Document') as mock_doc:
            # Mock document structure
            mock_paragraph = MagicMock()
            mock_paragraph.text = "Sample resume text"
            
            mock_doc_instance = MagicMock()
            mock_doc_instance.paragraphs = [mock_paragraph]
            mock_doc_instance.tables = []
            
            mock_doc.return_value = mock_doc_instance
            
            extractor = TextExtractor()
            result = extractor.extract_from_docx("fake_path.docx")
            
            assert result == "Sample resume text"
            mock_doc.assert_called_once_with("fake_path.docx")


class TestEntityExtractor:
    """Test cases for EntityExtractor class"""
    
    @patch('sereena_parser.main.spacy.load')
    def test_init_success(self, mock_spacy_load):
        """Test EntityExtractor initialization"""
        mock_nlp = MagicMock()
        mock_nlp.vocab = MagicMock()
        mock_spacy_load.return_value = mock_nlp
        
        extractor = EntityExtractor()
        
        assert extractor.nlp == mock_nlp
        assert len(extractor.all_skills) > 0
        mock_spacy_load.assert_called_once_with("en_core_web_sm")
    
    @patch('sereena_parser.main.spacy.load')
    def test_init_model_not_found(self, mock_spacy_load):
        """Test EntityExtractor initialization with missing spaCy model"""
        mock_spacy_load.side_effect = OSError("Model not found")
        
        with pytest.raises(OSError):
            EntityExtractor()
    
    @patch('sereena_parser.main.spacy.load')
    def test_extract_personal_info(self, mock_spacy_load):
        """Test personal information extraction"""
        # Mock spaCy model
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        
        # Mock named entities
        mock_person_entity = MagicMock()
        mock_person_entity.label_ = "PERSON"
        mock_person_entity.text = "John Doe"
        
        mock_location_entity = MagicMock()
        mock_location_entity.label_ = "GPE"
        mock_location_entity.text = "New York"
        
        mock_doc.ents = [mock_person_entity, mock_location_entity]
        mock_nlp.return_value = mock_doc
        mock_spacy_load.return_value = mock_nlp
        
        extractor = EntityExtractor()
        
        # Test text with email and phone
        test_text = "John Doe john.doe@email.com (555) 123-4567 New York"
        personal_info = extractor.extract_personal_info(test_text)
        
        assert personal_info.name == "John Doe"
        assert personal_info.email == "john.doe@email.com"
        assert personal_info.phone == "(555) 123-4567"
        assert personal_info.location == "New York"
    
    @patch('sereena_parser.main.spacy.load')
    def test_extract_skills(self, mock_spacy_load):
        """Test skills extraction"""
        mock_nlp = MagicMock()
        mock_spacy_load.return_value = mock_nlp
        
        extractor = EntityExtractor()
        
        # Test text with various skills
        test_text = "Experienced in Python, JavaScript, React, and AWS cloud services"
        skills = extractor.extract_skills(test_text)
        
        expected_skills = ["Python", "JavaScript", "React", "AWS"]
        for skill in expected_skills:
            assert skill in skills
    
    @patch('sereena_parser.main.spacy.load')
    def test_extract_education(self, mock_spacy_load):
        """Test education extraction"""
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        
        # Mock organization entity
        mock_org_entity = MagicMock()
        mock_org_entity.label_ = "ORG"
        mock_org_entity.text = "MIT"
        
        mock_doc.ents = [mock_org_entity]
        mock_nlp.return_value = mock_doc
        mock_spacy_load.return_value = mock_nlp
        
        extractor = EntityExtractor()
        
        test_text = "Education: Bachelor of Science in Computer Science, MIT, 2020"
        educations = extractor.extract_education(test_text)
        
        assert len(educations) > 0
        if educations:
            assert "Bachelor" in educations[0].degree
            assert educations[0].institution == "MIT"
    
    @patch('sereena_parser.main.spacy.load')
    def test_extract_certifications(self, mock_spacy_load):
        """Test certifications extraction"""
        mock_nlp = MagicMock()
        mock_spacy_load.return_value = mock_nlp
        
        extractor = EntityExtractor()
        
        test_text = "Certified AWS Solutions Architect and Google Cloud Professional"
        certifications = extractor.extract_certifications(test_text)
        
        assert len(certifications) > 0
        assert any("AWS" in cert for cert in certifications)


class TestResumeParser:
    """Test cases for ResumeParser class"""
    
    @patch('sereena_parser.main.EntityExtractor')
    @patch('sereena_parser.main.TextExtractor')
    def test_init(self, mock_text_extractor, mock_entity_extractor):
        """Test ResumeParser initialization"""
        parser = ResumeParser(max_workers=2)
        
        assert parser.max_workers == 2
        assert parser.text_extractor is not None
        assert parser.entity_extractor is not None
    
    @patch('sereena_parser.main.EntityExtractor')
    @patch('sereena_parser.main.TextExtractor')
    def test_parse_single_resume_pdf_success(self, mock_text_extractor_class, mock_entity_extractor_class):
        """Test successful parsing of a PDF resume"""
        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Mock text extractor
            mock_text_extractor = MagicMock()
            mock_text_extractor.extract_from_pdf.return_value = "Sample resume text with skills Python Java"
            mock_text_extractor_class.return_value = mock_text_extractor
            
            # Mock entity extractor
            mock_entity_extractor = MagicMock()
            mock_entity_extractor.extract_personal_info.return_value = PersonalInfo(
                name="John Doe",
                email="john@email.com"
            )
            mock_entity_extractor.extract_skills.return_value = ["Python", "Java"]
            mock_entity_extractor.extract_education.return_value = []
            mock_entity_extractor.extract_experience.return_value = []
            mock_entity_extractor.extract_certifications.return_value = []
            mock_entity_extractor_class.return_value = mock_entity_extractor
            
            parser = ResumeParser()
            file_path, resume_data = parser.parse_single_resume(temp_path)
            
            assert file_path == temp_path
            assert resume_data is not None
            assert resume_data.personal_info.name == "John Doe"
            assert resume_data.personal_info.email == "john@email.com"
            assert "Python" in resume_data.skills
            assert "Java" in resume_data.skills
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('sereena_parser.main.EntityExtractor')
    @patch('sereena_parser.main.TextExtractor')
    def test_parse_single_resume_file_not_found(self, mock_text_extractor_class, mock_entity_extractor_class):
        """Test parsing with non-existent file"""
        parser = ResumeParser()
        file_path, resume_data = parser.parse_single_resume("nonexistent.pdf")
        
        assert resume_data is None
    
    @patch('sereena_parser.main.EntityExtractor')
    @patch('sereena_parser.main.TextExtractor')
    def test_parse_single_resume_unsupported_format(self, mock_text_extractor_class, mock_entity_extractor_class):
        """Test parsing with unsupported file format"""
        # Create a temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            parser = ResumeParser()
            file_path, resume_data = parser.parse_single_resume(temp_path)
            
            assert resume_data is None
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('sereena_parser.main.EntityExtractor')
    @patch('sereena_parser.main.TextExtractor')
    def test_parse_multiple_resumes(self, mock_text_extractor_class, mock_entity_extractor_class):
        """Test parsing multiple resumes"""
        # Create temporary files
        temp_files = []
        try:
            for i in range(3):
                temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                temp_files.append(temp_file.name)
                temp_file.close()
            
            # Mock extractors
            mock_text_extractor = MagicMock()
            mock_text_extractor.extract_from_pdf.return_value = "Sample text"
            mock_text_extractor_class.return_value = mock_text_extractor
            
            mock_entity_extractor = MagicMock()
            mock_entity_extractor.extract_personal_info.return_value = PersonalInfo()
            mock_entity_extractor.extract_skills.return_value = []
            mock_entity_extractor.extract_education.return_value = []
            mock_entity_extractor.extract_experience.return_value = []
            mock_entity_extractor.extract_certifications.return_value = []
            mock_entity_extractor_class.return_value = mock_entity_extractor
            
            parser = ResumeParser(max_workers=2)
            results = parser.parse_multiple_resumes(temp_files)
            
            assert len(results) == 3
            # At least some results should be successful
            successful_results = [v for v in results.values() if v is not None]
            assert len(successful_results) > 0
            
        finally:
            # Clean up
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
    
    @patch('sereena_parser.main.EntityExtractor')
    @patch('sereena_parser.main.TextExtractor')
    def test_export_results(self, mock_text_extractor_class, mock_entity_extractor_class):
        """Test exporting results to JSON"""
        parser = ResumeParser()
        
        # Create sample results
        sample_resume_data = ResumeData(
            personal_info=PersonalInfo(name="John Doe", email="john@email.com"),
            skills=["Python", "Java"],
            education=[],
            experience=[],
            certifications=[],
            languages=[],
            summary="Sample summary"
        )
        
        results = {
            "resume1.pdf": sample_resume_data,
            "resume2.pdf": None  # Failed parsing
        }
        
        # Test export
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            parser.export_results(results, temp_path)
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            # Verify file size is reasonable (contains data)
            assert os.path.getsize(temp_path) > 10
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestDataClasses:
    """Test cases for data classes"""
    
    def test_personal_info_creation(self):
        """Test PersonalInfo data class"""
        info = PersonalInfo(
            name="John Doe",
            email="john@email.com",
            phone="555-1234",
            location="New York"
        )
        
        assert info.name == "John Doe"
        assert info.email == "john@email.com"
        assert info.phone == "555-1234"
        assert info.location == "New York"
    
    def test_education_creation(self):
        """Test Education data class"""
        education = Education(
            degree="Bachelor of Science",
            institution="MIT",
            year="2020",
            gpa="3.8"
        )
        
        assert education.degree == "Bachelor of Science"
        assert education.institution == "MIT"
        assert education.year == "2020"
        assert education.gpa == "3.8"
    
    def test_experience_creation(self):
        """Test Experience data class"""
        experience = Experience(
            job_title="Software Engineer",
            company="Tech Corp",
            duration="2020-2022",
            description="Developed applications"
        )
        
        assert experience.job_title == "Software Engineer"
        assert experience.company == "Tech Corp"
        assert experience.duration == "2020-2022"
        assert experience.description == "Developed applications"
    
    def test_resume_data_creation(self):
        """Test ResumeData data class"""
        personal_info = PersonalInfo(name="John Doe")
        resume_data = ResumeData(
            personal_info=personal_info,
            skills=["Python", "Java"],
            education=[],
            experience=[],
            certifications=[],
            languages=["English"],
            summary="Software developer"
        )
        
        assert resume_data.personal_info.name == "John Doe"
        assert "Python" in resume_data.skills
        assert resume_data.summary == "Software developer"


if __name__ == "__main__":
    pytest.main([__file__])