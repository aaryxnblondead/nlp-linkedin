"""
Utility to install a spaCy model if missing.
Usage (PowerShell):
  $env:SPACY_MODEL="en_core_web_sm"; python backend/scripts/install_spacy_model.py

Honors env SPACY_MODEL; defaults to en_core_web_sm.
"""
import os
import sys

model = os.getenv("SPACY_MODEL", "en_core_web_sm")

try:
    from spacy.cli.download import download as spacy_download
except Exception as e:
    print("spaCy not installed or CLI unavailable:", e)
    sys.exit(1)

try:
    print(f"Downloading spaCy model: {model}")
    spacy_download(model)  # type: ignore
    print("Done.")
except Exception as e:
    print("Failed to download model:", e)
    sys.exit(2)
