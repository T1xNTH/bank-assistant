"""Authenticated feedback using the existing OpenAPI contract."""

from typing import Literal

from fastapi import Depends, Response
from pydantic import BaseModel, Field, field_validator

from app import tracing
from app.contracts import User
from app.deps import get_current_user


class Feedback(BaseModel):
    trace_id: str
    score: Literal[-1, 1]
    comment: str = Field(default="", max_length=1000)

    @field_validator("score", mode="before")
    @classmethod
    def valid_score(cls, value: int) -> Literal[-1, 1]:
        if type(value) is not int or value not in (-1, 1):
            raise ValueError("Score must be -1 or 1")
        return value


def feedback(req: Feedback, user: User = Depends(get_current_user)) -> Response:
    tracing.score(req.trace_id, req.score, req.comment)
    return Response(status_code=204)
