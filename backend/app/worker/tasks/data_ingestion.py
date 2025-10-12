import os
from app.core import config
# Module A: Data Ingestion

def process_resume_file(resume_path):
    import os
    ext = os.path.splitext(resume_path)[1].lower()
    if ext == '.txt':
        with open(resume_path, 'r', encoding='utf-8') as f:
            return f.read()
    try:
        # sereena_parser may raise SystemExit on missing deps; catch broadly
        from sereena_parser import ResumeParser  # type: ignore
        parser = ResumeParser()
        _, resume_data = parser.parse_single_resume(resume_path)
        if resume_data and hasattr(resume_data, 'raw_text'):
            return resume_data.raw_text
    except BaseException:
        # Fallback to built-in parsers if sereena_parser is unavailable or fails
        pass
    # Fallback: use PyMuPDF or doc/docx logic
    try:
        if ext == '.pdf':
            import fitz
            with fitz.open(resume_path) as doc:
                # Support both PyMuPDF APIs across versions
                pages_text = []
                for page in doc:
                    text_getter = getattr(page, "get_text", None)
                    if callable(text_getter):
                        try:
                            pages_text.append(text_getter("text"))
                        except TypeError:
                            pages_text.append(text_getter())
                    else:
                        legacy_getter = getattr(page, "getText", None)
                        if callable(legacy_getter):
                            try:
                                pages_text.append(legacy_getter("text"))
                            except TypeError:
                                pages_text.append(legacy_getter())
                        else:
                            pages_text.append("")
                return "\n".join(pages_text)
        elif ext == '.docx':
            import docx
            doc = docx.Document(resume_path)
            return "\n".join([para.text for para in doc.paragraphs])
        elif ext == '.doc':
            # Try textract first if available
            try:
                import textract  # type: ignore
                content = textract.process(resume_path)
                if isinstance(content, bytes):
                    return content.decode('utf-8', errors='ignore')
                return str(content)
            except Exception:
                pass
            # Windows-only fallback: use Word COM automation if available
            try:
                import tempfile
                import pythoncom  # type: ignore
                import win32com.client  # type: ignore
                pythoncom.CoInitialize()
                word = win32com.client.Dispatch('Word.Application')
                word.Visible = False
                doc = word.Documents.Open(resume_path)
                tmp_txt = tempfile.mktemp(suffix='.txt')
                # 2 = wdFormatText
                doc.SaveAs(tmp_txt, FileFormat=2)
                doc.Close(False)
                word.Quit()
                with open(tmp_txt, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception:
                pass
    except Exception:
        pass
    return ""

def scrape_linkedin_profile(linkedin_url):
    # Credentials must come from environment variables
    # Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD before running
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    engine = config.SCRAPER_ENGINE
    try:
        if engine == "selenium":
            from linkedin_scraper import Person, actions
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            headless = (os.getenv("HEADLESS", "true").lower() == "true")
            chrome_options = Options()
            if headless:
                # Use new headless where available
                chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(options=chrome_options)
            # Try linkedin_scraper login; if it fails, do manual login
            if email and password:
                try:
                    actions.login(driver, email, password)
                except Exception:
                    try:
                        driver.get('https://www.linkedin.com/login')
                        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.NAME, 'session_key')))
                        driver.find_element(By.NAME, 'session_key').send_keys(email)
                        driver.find_element(By.NAME, 'session_password').send_keys(password)
                        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
                        # wait for either feed or me nav
                        WebDriverWait(driver, 12).until(lambda d: 'feed' in d.current_url or 'linkedin.com' in d.current_url)
                    except Exception:
                        pass
            # Attempt library extraction first
            person = None
            try:
                person = Person(linkedin_url, driver=driver)
            except Exception:
                try:
                    driver.get(linkedin_url)
                except Exception:
                    pass
            # Extract core fields with graceful fallback
            name = getattr(person, 'name', None) if person else None
            headline = getattr(person, 'headline', None) if person else None
            experiences = getattr(person, 'experiences', []) or [] if person else []
            educations = getattr(person, 'educations', []) or [] if person else []
            interests = getattr(person, 'interests', []) or [] if person else []
            # Many implementations don't expose skills/projects/posts; attempt best-effort
            endorsed_skills = getattr(person, 'skills', []) or [] if person else []
            projects = getattr(person, 'projects', []) or [] if person else []
            posts = getattr(person, 'posts', []) or [] if person else []
            activity_timestamps = getattr(person, 'activity_timestamps', []) or [] if person else []

            def norm_list(vals):
                try:
                    return [str(v) for v in vals if v is not None]
                except Exception:
                    return []

            # Try to detect URLs within project values
            import re
            def to_project_dicts(items):
                out = []
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict):
                            name = it.get('name') or it.get('title') or it.get('project') or ''
                            url = it.get('url') or it.get('link') or ''
                            # search any string fields for a URL
                            if not url:
                                for v in it.values():
                                    if isinstance(v, str):
                                        m = re.search(r"https?://\S+", v)
                                        if m:
                                            url = m.group(0)
                                            break
                            out.append({"name": str(name)[:200], "url": url})
                        else:
                            s = str(it)
                            m = re.search(r"https?://\S+", s)
                            url = m.group(0) if m else ''
                            out.append({"name": s[:200], "url": url})
                return out

            profile = {
                "name": name,
                "headline": headline,
                "experiences": norm_list(experiences),
                "educations": norm_list(educations),
                "interests": list(interests) if isinstance(interests, list) else [],
                "endorsed_skills": norm_list(endorsed_skills),
                "projects": to_project_dicts(projects),
                "posts": norm_list(posts),
                "activity_timestamps": norm_list(activity_timestamps),
            }
            # Fallback naive extraction if most fields are empty
            try:
                empty = not any([
                    profile.get('name'), profile.get('headline'), profile.get('projects'), profile.get('endorsed_skills')
                ])
                if empty:
                    driver.get(linkedin_url)
                    # Try to grab visible name/headline
                    try:
                        h1s = driver.find_elements(By.TAG_NAME, 'h1')
                        if h1s:
                            profile['name'] = (h1s[0].text or '').strip() or profile.get('name')
                    except Exception:
                        pass
                    try:
                        # LinkedIn often uses 'div.text-body-medium.break-words' for headline
                        elems = driver.find_elements(By.CSS_SELECTOR, 'div.text-body-medium.break-words')
                        if elems:
                            profile['headline'] = (elems[0].text or '').strip() or profile.get('headline')
                    except Exception:
                        pass
                    # Heuristic projects via anchors containing 'project'
                    try:
                        anchors = driver.find_elements(By.TAG_NAME, 'a')
                        proj = []
                        for a in anchors[:500]:
                            try:
                                href = a.get_attribute('href') or ''
                                text = (a.text or '').strip()
                                if not href:
                                    continue
                                if ('project' in text.lower()) or ('project' in href.lower()):
                                    url = href
                                    name_txt = text or url
                                    proj.append({"name": name_txt[:200], "url": url})
                            except Exception:
                                continue
                        if proj:
                            profile['projects'] = proj
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                driver.quit()
            except Exception:
                pass
            # Ensure a dict is always returned
            return profile if profile else {"warning": "empty profile", "url": linkedin_url, "engine": engine}
        elif engine == "playwright":
            # Playwright fallback with persistent context and optional headless
            from playwright.sync_api import sync_playwright  # type: ignore
            import re
            headless = (os.getenv("HEADLESS", "true").lower() == "true")
            storage_dir = os.path.abspath(os.path.join("backend", ".pw-linkedin"))
            os.makedirs(storage_dir, exist_ok=True)
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(user_data_dir=storage_dir, headless=headless)
                page = context.new_page()
                page.goto(linkedin_url, wait_until="domcontentloaded")
                # Try credential login if on login page
                if email and password and ('login' in page.url or 'session' in page.url):
                    try:
                        page.fill('input[name="session_key"]', email)
                        page.fill('input[name="session_password"]', password)
                        page.click('button[type="submit"]')
                        page.wait_for_timeout(2000)
                        page.goto(linkedin_url, wait_until="domcontentloaded")
                    except Exception:
                        pass
                # Extract anchors that look like projects
                anchors = page.locator('a')
                proj = []
                try:
                    count = anchors.count()
                except Exception:
                    count = 0
                for i in range(min(600, count)):
                    try:
                        href = anchors.nth(i).get_attribute('href') or ''
                        text = anchors.nth(i).inner_text() or ''
                        if not href:
                            continue
                        if ('project' in text.lower()) or ('project' in href.lower()):
                            url = href if href.startswith('http') else f"https://www.linkedin.com{href}" if href.startswith('/') else href
                            name = (text or '').strip() or url
                            proj.append({"name": name[:200], "url": url})
                    except Exception:
                        continue
                # Simple headline extraction
                try:
                    headline_text = page.locator('[data-generated-suggestion-target="headline"]').first.inner_text()
                except Exception:
                    headline_text = None
                try:
                    context.close()
                except Exception:
                    pass
                return {
                    "headline": headline_text,
                    "projects": proj,
                    "url": linkedin_url,
                    "note": "playwright scrape (best-effort)",
                }
    except Exception as e:
        return {"error": str(e), "url": linkedin_url, "engine": engine}
    # Final guard: never return None
    return {"error": "scraper returned no data", "url": linkedin_url, "engine": engine}
