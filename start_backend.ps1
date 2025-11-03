# PowerShell script to reliably start FastAPI backend from project root
Push-Location (Join-Path $PSScriptRoot "backend")

# --- Language Model Configuration ---
# Set the provider to "google" or "hf" (Hugging Face)
# Prefer existing environment or .env; do not hardcode secrets here
if (-not $env:GEN_PROVIDER) { $env:GEN_PROVIDER = "google" }

# Enable AI-assisted enrichment for NER when using LLM env
if (-not $env:USE_LLM_NER_ENRICH) { $env:USE_LLM_NER_ENRICH = "true" }


if (-not $env:SCRAPER_ENGINE) { $env:SCRAPER_ENGINE = "selenium" }
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
