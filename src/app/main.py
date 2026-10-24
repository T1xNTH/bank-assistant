"""FastAPI entrypoint. Owner: B (routes, auth, errors); /ask logic: A via Answerer."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import Depends, FastAPI

from app.contracts import Answerer, User
from app.deps import get_answerer, get_current_user
from app.schemas import AskRequest, AskResponse

app = FastAPI(title="bank-assistant", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    user: User = Depends(get_current_user),
    answerer: Answerer = Depends(get_answerer),
) -> AskResponse:
    result = answerer.answer(req.question, user, req.mode)
    return AskResponse(**asdict(result))
