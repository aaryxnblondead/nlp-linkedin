import os
from app.core import config
# Module A: Data Ingestion

def process_resume_file(resume_path):
    import os
    import re
    import zipfile

    def _clean_text(s: str) -> str:
        if not s:
            return ""
        # Normalize newlines, drop control chars except tab/newline, collapse excessive blank lines
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", s)
        # Fix common PDF hyphenation across line breaks: "word-\nnext" -> "wordnext"
        s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
        # Trim trailing spaces on lines
        s = "\n".join([ln.rstrip() for ln in s.splitlines()])
        # Collapse 3+ blank lines to 2
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()

    def _is_docx_container(path: str) -> bool:
        try:
            if not zipfile.is_zipfile(path):
                return False
            with zipfile.ZipFile(path) as z:
                # A valid DOCX should contain word/document.xml
                return any(n.lower() == "word/document.xml" for n in z.namelist())
        except Exception:
            return False

    def _extract_pdf(path: str) -> str:
        text = ""
        # First: PyMuPDF
        try:
            import fitz  # type: ignore
            with fitz.open(path) as doc:
                parts = []
                for page in doc:
                    getter = getattr(page, "get_text", None)
                    if callable(getter):
                        try:
                            parts.append(getter("text"))
                        except TypeError:
                            parts.append(getter())
                    else:
                        legacy = getattr(page, "getText", None)
                        if callable(legacy):
                            try:
                                parts.append(legacy("text"))
                            except TypeError:
                                parts.append(legacy())
                text = "\n".join(parts)
        except Exception:
            text = ""
        if text and len(text) >= 80:
            return _clean_text(text)
        # Fallback: pdfminer.six
        try:
            from pdfminer.high_level import extract_text  # type: ignore
            txt = extract_text(path) or ""
            if txt and len(txt) > len(text):
                text = txt
        except Exception:
            pass
        if text and len(text) >= 40:
            return _clean_text(text)
        # Optional OCR fallback if pytesseract and PIL are installed
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
            import fitz  # type: ignore
            with fitz.open(path) as doc:
                ocr_parts = []
                for i in range(len(doc)):
                    page = doc[i]
                    # Limit to first 8 pages for OCR to keep it light
                    if i >= 8:
                        break
                    # Try modern API
                    pix = None
                    try:
                        get_pixmap = getattr(page, "get_pixmap", None)
                        if callable(get_pixmap):
                            pix = get_pixmap(dpi=200)  # type: ignore[call-arg]
                    except Exception:
                        pix = None
                    if pix is None:
                        # Older PyMuPDF fallback
                        try:
                            Matrix = getattr(fitz, "Matrix", None)
                            getPixmap = getattr(page, "getPixmap", None)
                            if callable(Matrix) and callable(getPixmap):
                                mat = Matrix(200/72.0, 200/72.0)
                                pix = getPixmap(matrix=mat)  # type: ignore[attr-defined]
                        except Exception:
                            pix = None
                    if pix is not None:
                        try:
                            w = getattr(pix, "width", None)
                            h = getattr(pix, "height", None)
                            samples = getattr(pix, "samples", None)
                            if w and h and samples:
                                img = Image.frombytes("RGB", (int(w), int(h)), samples)
                                ocr_parts.append(pytesseract.image_to_string(img))
                        except Exception:
                            continue
                if ocr_parts:
                    ocr_text = "\n".join(ocr_parts)
                    if len(ocr_text) > len(text):
                        text = ocr_text
        except Exception:
            pass
        return _clean_text(text)

    def _extract_docx(path: str) -> str:
        try:
            import docx  # type: ignore
            d = docx.Document(path)
            lines = [p.text for p in d.paragraphs]
            # Include table text as well
            try:
                for table in d.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            t = (cell.text or "").strip()
                            if t:
                                lines.append(t)
            except Exception:
                pass
            return _clean_text("\n".join(lines))
        except Exception:
            # As a last resort, try reading the raw XML
            try:
                with zipfile.ZipFile(path) as z:
                    xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
                # Strip XML tags
                xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
                xml = re.sub(r"<[^>]+>", " ", xml)
                return _clean_text(xml)
            except Exception:
                return ""

    def _extract_doc(path: str) -> str:
        # Some ".doc" files are actually docx containers; detect and treat accordingly
        if _is_docx_container(path):
            return _extract_docx(path)
        # Some mis-labeled .doc might still be zip packages (themes, etc.); try extracting text from XML parts
        try:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path) as z:
                    buff = []
                    for name in z.namelist():
                        if name.lower().endswith('.xml'):
                            try:
                                xml = z.read(name).decode('utf-8', errors='ignore')
                                # Remove tags and keep text
                                xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
                                xml = re.sub(r"<[^>]+>", " ", xml)
                                buff.append(xml)
                            except Exception:
                                continue
                    if buff:
                        return _clean_text("\n".join(buff))
        except Exception:
            pass
        # Try if the file is plain XML on disk (Office XML part saved as .doc)
        try:
            with open(path, 'rb') as f:
                data = f.read()
            txt = None
            for enc in ('utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1'):
                try:
                    txt = data.decode(enc)
                    break
                except Exception:
                    continue
            if not txt:
                txt = data.decode('utf-8', errors='ignore')
            # If it looks like XML-ish content, strip tags
            sample = txt[:2000]
            if ('<' in sample and '>' in sample) and (sample.count('<') >= 3):
                xml = txt
                xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
                xml = re.sub(r"<[^>]+>", " ", xml)
                return _clean_text(xml)
        except Exception:
            pass
        # Try textract first
        try:
            import textract  # type: ignore
            content = textract.process(path)
            if isinstance(content, bytes):
                return _clean_text(content.decode('utf-8', errors='ignore'))
            return _clean_text(str(content))
        except Exception:
            pass
        # Try antiword if installed
        try:
            import subprocess, shlex
            cmd = f"antiword -m UTF-8 '{path}'"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            out = result.stdout.decode('utf-8', errors='ignore')
            if out and len(out) > 20:
                return _clean_text(out)
        except Exception:
            pass
        # Try catdoc if installed
        try:
            import subprocess
            result = subprocess.run(["catdoc", path], capture_output=True)
            out = result.stdout.decode('utf-8', errors='ignore')
            if out and len(out) > 20:
                return _clean_text(out)
        except Exception:
            pass
        # Windows Word COM automation
        try:
            import tempfile
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
            pythoncom.CoInitialize()
            word = win32com.client.Dispatch('Word.Application')
            word.Visible = False
            doc = word.Documents.Open(path)
            tmp_txt = tempfile.mktemp(suffix='.txt')
            # 2 = wdFormatText
            doc.SaveAs(tmp_txt, FileFormat=2)
            doc.Close(False)
            word.Quit()
            with open(tmp_txt, 'r', encoding='utf-8', errors='ignore') as f:
                return _clean_text(f.read())
        except Exception:
            pass
        # Last-ditch: attempt to pull readable ASCII from binary
        try:
            with open(path, 'rb') as f:
                data = f.read()
            textish = []
            cur = []
            for b in data:
                if 32 <= b <= 126 or b in (9, 10, 13):
                    cur.append(chr(b))
                else:
                    if len(cur) >= 5:
                        textish.append(''.join(cur))
                    cur = []
            if len(cur) >= 5:
                textish.append(''.join(cur))
            if textish:
                return _clean_text('\n'.join(textish))
        except Exception:
            pass
        return ""

    ext = os.path.splitext(resume_path)[1].lower()

    # Fast path: plain text
    if ext == '.txt':
        try:
            with open(resume_path, 'r', encoding='utf-8', errors='ignore') as f:
                return _clean_text(f.read())
        except Exception:
            return ""

    # 1) Primary: third-party parser (sereena_parser)
    parsed_text = ""
    try:
        from sereena_parser import ResumeParser  # type: ignore
        parser = ResumeParser()
        _, resume_data = parser.parse_single_resume(resume_path)
        if resume_data and hasattr(resume_data, 'raw_text'):
            parsed_text = _clean_text(getattr(resume_data, 'raw_text') or "")
    except BaseException:
        parsed_text = ""

    # If parser returned too little text, fall back to our robust extractors
    MIN_LEN = 120
    if parsed_text and len(parsed_text) >= MIN_LEN:
        return parsed_text

    # 2) Robust fallbacks by extension and content
    try:
        if ext == '.pdf':
            return _extract_pdf(resume_path)
        if ext == '.docx' or _is_docx_container(resume_path):
            return _extract_docx(resume_path)
        if ext == '.doc':
            return _extract_doc(resume_path)
    except Exception:
        pass

    # 3) Last resort: try a generic read for any text content
    try:
        with open(resume_path, 'rb') as f:
            data = f.read()
        sample = data[:262144].decode('utf-8', errors='ignore')
        # Heuristic: if there are lots of NULs it isn't clean text
        if sample.count('\x00') < 10:
            return _clean_text(sample)
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
