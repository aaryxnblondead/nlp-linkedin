from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.user import UserRole
from app.api.v1.endpoints.deps import get_current_user, require_role
from app.models.applicant import Applicant, Resume, Insights
from app.services.embeddings import retrieve_kb_texts, retrieve_corpus_texts
from app.services.generation import generate

router = APIRouter()


def _authz_check(applicant: Applicant, current_user) -> None:
    role = getattr(current_user, 'role', None)
    uid = getattr(current_user, 'id', None)
    if role == UserRole.recruiter:
        return
    if role == UserRole.applicant and getattr(applicant, 'user_id', None) == uid:
        return
    raise HTTPException(status_code=403, detail="Not authorized to chat for this applicant")


@router.post("/chat/{applicant_id}")
def chat_applicant(
    applicant_id: int,
    payload: Dict[str, Any] = Body(..., example={
        "messages": [
            {"role": "user", "content": "Summarize this applicant's experience in databases."}
        ],
        "top_k": 6,
        "max_new_tokens": 256
    }),
    current_user=Depends(get_current_user),
):
    """Conversational chat grounded strictly in the applicant's data (resume, structured, insights).

    Body schema:
    - messages: list of {role: 'user'|'assistant'|'system', content: str}; we use the latest user message.
    - top_k: how many KB chunks to retrieve (default 6)
    - max_new_tokens: generation cap (default 256)
    """
    db: Session = SessionLocal()
    try:
        app = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Applicant not found")
        _authz_check(app, current_user)

        msgs: List[Dict[str, str]] = list(payload.get("messages") or [])
        if not msgs:
            raise HTTPException(status_code=400, detail="messages is required")
        # Take the latest user message as the question
        question = None
        for m in reversed(msgs):
            if (m.get("role") or "").lower() == "user" and (m.get("content") or "").strip():
                question = str(m["content"]).strip()
                break
        if not question:
            raise HTTPException(status_code=400, detail="No user question provided in messages")

        top_k = int(payload.get("top_k") or 6)
        max_new_tokens = int(payload.get("max_new_tokens") or 256)

        # Applicant-specific namespace created by embeddings service
        namespace = f"applicant_{applicant_id}"

        # Retrieve only this applicant's data to keep answers strictly grounded
        contexts: List[str] = []
        try:
            contexts = retrieve_kb_texts(namespace, question, k=top_k) or []
        except Exception:
            contexts = []

        # Guardrails: If we have no context, avoid hallucinations
        if not contexts:
            return {
                "reply": "I don't have enough information in this applicant's data to answer that.",
                "used_chunks": [],
            }

        # Hard grounding via prompt instruction is handled inside generate()'s build_prompt
        answer = generate(question, contexts, max_new_tokens=max_new_tokens) or ""
        if not answer.strip():
            answer = "I don't have enough information in this applicant's data to answer that."

        # Return minimal chat-like structure
        return {
            "reply": answer.strip(),
            "used_chunks": contexts,
        }
    finally:
        db.close()


@router.post("/chat")
def chat_global(
    payload: Dict[str, Any] = Body(..., example={
        "messages": [{"role": "user", "content": "List applicants with Kubernetes experience."}],
        "top_k": 8,
        "max_new_tokens": 256
    }),
    current_user=Depends(get_current_user),
):
    """Conversational chat grounded in the entire corpus (all applicants).

    Authorization: any logged-in user.
    """
    msgs: List[Dict[str, str]] = list(payload.get("messages") or [])
    if not msgs:
        raise HTTPException(status_code=400, detail="messages is required")
    # Latest user question
    question = None
    for m in reversed(msgs):
        if (m.get("role") or "").lower() == "user" and (m.get("content") or "").strip():
            question = str(m["content"]).strip()
            break
    if not question:
        raise HTTPException(status_code=400, detail="No user question provided in messages")

    top_k = int(payload.get("top_k") or 8)
    max_new_tokens = int(payload.get("max_new_tokens") or 256)

    contexts: List[str] = []
    try:
        contexts = retrieve_corpus_texts(question, k=top_k) or []
    except Exception:
        contexts = []

    if not contexts:
        return {
            "reply": "I don't have enough information in the corpus to answer that.",
            "used_chunks": [],
        }

    answer = generate(question, contexts, max_new_tokens=max_new_tokens) or ""
    if not answer.strip():
        answer = "I don't have enough information in the corpus to answer that."

    return {
        "reply": answer.strip(),
        "used_chunks": contexts,
    }
