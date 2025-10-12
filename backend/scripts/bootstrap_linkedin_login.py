import os
import sys
import time
import pathlib

# Bootstrap a persistent Playwright Chromium context for LinkedIn.
# Purpose: let a human complete login once; cookies will persist for future scrapes.
# Usage:
#   python backend/scripts/bootstrap_linkedin_login.py
# Steps:
#   1) A Chromium window opens.
#   2) Navigate to linkedin.com/login (if not already), log in manually (handle 2FA/captcha if any).
#   3) Return to terminal and press Enter to finish; session cookies are saved to backend/.pw-linkedin

STORAGE_DIR = pathlib.Path("backend/.pw-linkedin").resolve()

try:
    from playwright.sync_api import sync_playwright  # type: ignore
except Exception as e:
    print("ERROR: Playwright not installed. Install it and browsers, e.g.:\n  pip install playwright\n  playwright install\n")
    sys.exit(1)

if __name__ == "__main__":
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    headless = (os.getenv("HEADLESS", "false").lower() == "true")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=str(STORAGE_DIR), headless=headless)
        page = context.new_page()
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        print("A Chromium window should be open. Please log into LinkedIn in that window.")
        print("When you finish (and see your feed or profile), return here and press Enter to save the session.")
        try:
            input()
        except KeyboardInterrupt:
            pass
        try:
            context.close()
        except Exception:
            pass
        print(f"Saved session to: {STORAGE_DIR}")
