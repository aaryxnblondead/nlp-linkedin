from app.worker.tasks.data_ingestion import process_resume_file, scrape_linkedin_profile
from app.worker.tasks.intelligence_engine import create_structured_resume, generate_candidate_insights
from app.services.normalize import normalize_structured_resume
from app.models.applicant import Applicant, Resume, LinkedInProfile, Insights
from app.db import SessionLocal
from app.worker.celery_app import celery_app
from app.services.embeddings import chunk_texts, upsert_applicant_kb, add_corpus_texts
from app.services.skills_dict import update_aliases, normalize_skill

@celery_app.task
def process_applicant_pipeline(applicant_id, resume_path, linkedin_url):
    db = SessionLocal()
    try:
        # mark processing
        app = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        try:
            db.query(Applicant).filter(Applicant.id == applicant_id).update({Applicant.status: "processing"})
            db.commit()
        except Exception:
            pass
            db.commit()

        # Step 1: Parse resume
        resume_text = process_resume_file(resume_path)
        # Step 2: Optionally scrape LinkedIn (disabled by default)
        from app.core import config
        linkedin_data = {}
        if getattr(config, 'USE_LINKEDIN_SCRAPE', False) and linkedin_url:
            try:
                linkedin_data = scrape_linkedin_profile(linkedin_url) or {}
            except Exception:
                linkedin_data = {"error": "scrape_disabled_or_failed"}
        # Step 3: Structure resume (ignores LinkedIn per policy)
        structured_resume = create_structured_resume(resume_text, linkedin_data)
        # Step 3.0: Normalize and enrich structured fields (skills canonicalization, name/org casing, email casing)
        try:
            structured_resume = normalize_structured_resume(structured_resume)
        except Exception:
            pass
        # Step 3.1: Update Applicant name/email. Replace placeholder filename-like names.
        try:
            sr_name = (structured_resume.get("name") or "").strip()
            sr_email = (structured_resume.get("email") or "").strip()
            updates = {}
            current_name = str(getattr(app, "name", "") or "").strip() if app else ""
            current_email = str(getattr(app, "email", "") or "").strip() if app else ""
            def looks_like_filename(n: str) -> bool:
                nlow = (n or "").lower()
                if any(x in nlow for x in ["resume", "cv", "_", "-", ".doc", ".pdf", ".docx"]):
                    return True
                if any(ch.isdigit() for ch in nlow):
                    return True
                return False
            if app and sr_name and (not current_name or looks_like_filename(current_name)):
                updates[Applicant.name] = sr_name
            if app and (not current_email) and sr_email:
                updates[Applicant.email] = sr_email
            if updates:
                db.query(Applicant).filter(Applicant.id == applicant_id).update(updates)
                db.commit()
        except Exception:
            # Non-fatal; continue pipeline even if update fails
            db.rollback()

        # Step 4: Generate insights
        insights = generate_candidate_insights(structured_resume)

        # Step 6: Save to DB
        resume = Resume(applicant_id=applicant_id, raw_text=resume_text, structured_data=structured_resume)
        # Optionally persist LinkedIn profile only if scraping enabled and we got meaningful data
        linkedin = None
        if getattr(config, 'USE_LINKEDIN_SCRAPE', False) and linkedin_data and isinstance(linkedin_data, dict) and not linkedin_data.get('error'):
            linkedin = LinkedInProfile(applicant_id=applicant_id, profile_data=linkedin_data)
        insight = Insights(
            applicant_id=applicant_id,
            rating=insights.get("rating"),
            summary=insights.get("summary"),
            sentiment_score=insights.get("sentiment_score"),
            activity_score=insights.get("activity_score"),
            top_endorsed_skills=insights.get("top_endorsed_skills"),
            projects=insights.get("projects"),
            experience_years=insights.get("experience_years"),
            consistency_flags=insights.get("consistency_flags"),
        )
        db.add(resume)
        if linkedin is not None:
            db.add(linkedin)
        db.add(insight)
        try:
            db.query(Applicant).filter(Applicant.id == applicant_id).update({Applicant.status: "processed"})
        except Exception:
            pass
        db.commit()

        # ----- RAG indexing: add applicant data (raw + NER/enriched structured + insights) into KB and global corpus -----
        try:
            combined_chunks = []
            combined_metas = []

            # 1) Raw resume text
            if resume_text:
                rc = chunk_texts([resume_text])
                combined_chunks.extend(rc)
                combined_metas.extend([
                    {"source": getattr(app, 'resume_path', None), "applicant_id": applicant_id, "kind": "resume_raw"}
                    for _ in rc
                ])

            # 2) Human-readable structured fields derived from NER and optional LLM enrichment
            try:
                structured_texts = []
                if structured_resume:
                    skills = structured_resume.get("skills") or []
                    titles = structured_resume.get("titles") or []
                    orgs = structured_resume.get("organizations") or []
                    locs = structured_resume.get("locations") or []
                    edu = structured_resume.get("education") or []
                    exp = structured_resume.get("experience") or []

                    if skills:
                        structured_texts.append("Skills: " + ", ".join([str(s) for s in skills if s]))
                    if titles:
                        structured_texts.append("Titles: " + ", ".join([str(t) for t in titles if t]))
                    if orgs:
                        structured_texts.append("Organizations: " + ", ".join([str(o) for o in orgs if o]))
                    if locs:
                        structured_texts.append("Locations: " + ", ".join([str(l) for l in locs if l]))

                    for e in edu[:30]:
                        dl = []
                        if e.get("degree"): dl.append(str(e.get("degree")))
                        if e.get("field"): dl.append(str(e.get("field")))
                        if e.get("institution"): dl.append(str(e.get("institution")))
                        if dl:
                            structured_texts.append("Education: " + " | ".join(dl))

                    for x in exp[:80]:
                        parts = []
                        if x.get("title"): parts.append(str(x.get("title")))
                        if x.get("company"): parts.append(str(x.get("company")))
                        if x.get("location"): parts.append(str(x.get("location")))
                        se = " - ".join([p for p in [str(x.get("start") or ""), str(x.get("end") or "")] if p])
                        if se: parts.append(se)
                        snippet = str(x.get("snippet") or "")
                        line = "Experience: " + " | ".join(parts)
                        if snippet:
                            line += f" | {snippet}"
                        structured_texts.append(line)

                if structured_texts:
                    sc = chunk_texts(structured_texts)
                    combined_chunks.extend(sc)
                    combined_metas.extend([
                        {"source": getattr(app, 'resume_path', None), "applicant_id": applicant_id, "kind": "ner_structured"}
                        for _ in sc
                    ])
            except Exception:
                pass

            # 3) Insights summary
            try:
                if insights and insights.get("summary"):
                    ic = chunk_texts([str(insights.get("summary"))])
                    combined_chunks.extend(ic)
                    combined_metas.extend([
                        {"source": getattr(app, 'resume_path', None), "applicant_id": applicant_id, "kind": "insights_summary"}
                        for _ in ic
                    ])
            except Exception:
                pass

            # 4) Applicant profile: ensure the corpus contains explicit name/email/rating/experience so the chatbot can list applicants
            try:
                sr_name = str((structured_resume or {}).get("name") or "").strip()
                app_name = sr_name or (str(getattr(app, "name", "") or "").strip())
                sr_email = str((structured_resume or {}).get("email") or "").strip()
                app_email = sr_email or (str(getattr(app, "email", "") or "").strip())
                rating_val = None
                exp_val = None
                try:
                    rating_val = insights.get("rating") if isinstance(insights, dict) else None
                    exp_val = insights.get("experience_years") if isinstance(insights, dict) else None
                except Exception:
                    pass
                prof_parts = []
                if app_name:
                    prof_parts.append(f"Name: {app_name}")
                if app_email:
                    prof_parts.append(f"Email: {app_email}")
                if rating_val is not None:
                    prof_parts.append(f"Rating: {rating_val}")
                if exp_val is not None:
                    prof_parts.append(f"Experience: {exp_val} yrs")
                if getattr(app, 'linkedin_url', None):
                    prof_parts.append(f"LinkedIn: {getattr(app, 'linkedin_url')}")
                profile_line = ("Applicant Profile | " + " | ".join(prof_parts)).strip()
                if profile_line and profile_line != "Applicant Profile |":
                    pc = chunk_texts([profile_line])
                    combined_chunks.extend(pc)
                    combined_metas.extend([
                        {"source": getattr(app, 'resume_path', None), "applicant_id": applicant_id, "kind": "applicant_profile"}
                        for _ in pc
                    ])
            except Exception:
                pass

            if combined_chunks:
                # Upsert into applicant-specific KB
                namespace = upsert_applicant_kb(applicant_id, combined_chunks)
                # Add to global corpus with per-chunk metadata
                add_corpus_texts(combined_chunks, combined_metas)
                # Persist namespace for the applicant insights row if available
                try:
                    rec = db.query(Insights).filter(Insights.applicant_id == applicant_id).first()
                    if rec:
                        db.query(Insights).filter(Insights.id == rec.id).update({Insights.kb_namespace: namespace})
                        db.commit()
                except Exception:
                    db.rollback()
        except Exception:
            # Non-fatal if Chroma isn't available
            pass

        # ----- Dynamic skills dictionary enrichment from insights ----
        try:
            skills = []
            skills_list = structured_resume.get("skills", []) if structured_resume else []
            skills.extend([normalize_skill(str(s)) for s in skills_list if s])
            # From insights summary, extract rudimentary skill tokens (lowercase words that match known patterns)
            summ = str(insights.get("summary") or "").lower()
            tokens = [t.strip(",.;:()[]{}") for t in summ.split() if t and len(t) <= 30]
            skills.extend([normalize_skill(t) for t in tokens if normalize_skill(t)])
            # Build alias->canonical pairs as identity for unknown skills; actual alias expansion will run via ensure_aliases in normalize path
            pairs = []
            for s in set(skills):
                if s:
                    pairs.append((s, s))
            if pairs:
                update_aliases(pairs)
        except Exception:
            pass
        return True
    except Exception:
        try:
            db.query(Applicant).filter(Applicant.id == applicant_id).update({Applicant.status: "failed"})
            db.commit()
        except Exception:
            pass
            db.commit()
        raise
    finally:
        db.close()
