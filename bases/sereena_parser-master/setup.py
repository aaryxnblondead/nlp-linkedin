from setuptools import setup, find_packages

# Read the README file for the long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="sereena-parser",
    version="2.0.0",
    description="Production-ready resume parser with multi-threading support for PDF and DOCX files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sereena Thomas",
    author_email="crce.10278.ceb@gmail.com",
    url="https://github.com/joelpawar08/sereena-parser",
    license="MIT",
    packages=find_packages(where=".", include=["sereena_parser*"]),
    install_requires=[
        
        "pypdf",
        "pdfplumber>=0.10.3",
        "python-docx>=1.1.0",
        "spacy>=3.7.2",
        "pandas>=2.1.4",
        "email-validator>=2.1.0",
        "numpy>=1.25.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "sereena-parser = sereena_parser.main:cli_main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Office/Business",
    ],
    keywords=["resume", "parser", "cv", "pdf", "docx", "nlp", "recruitment"],
    python_requires=">=3.8",
    project_urls={
        "Homepage": "https://github.com/yourusername/sereena-parser",
        "Repository": "https://github.com/yourusername/sereena-parser",
        "Bug Tracker": "https://github.com/yourusername/sereena-parser/issues",
    },
)