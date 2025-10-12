# Dependency Pruning (2025-10-12)

This pass trims dev-only dependencies from production install sets while preserving runtime features.

Changes:
- backend/requirements.txt: removed pytest (dev-only)
- Added backend/requirements-dev.txt: extends requirements.txt and adds pytest

Notes:
- Heavy optional providers (transformers, torch, playwright, textract, tabula, pytesseract) are NOT present and not added. Some scripts reference them; they remain optional by design.
- Runtime features validated by tests will run under requirements-dev.txt which includes pytest.

Next steps (optional):
- Split selenium/linkedin-scraper into a separate extras file if you want to avoid installing scraping stack in non-scrape deployments.
- Consider adding lint/type check tooling under dev requirements (ruff, mypy) if desired.
