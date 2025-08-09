from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, Field, field_validator


class CalculateRequest(BaseModel):
    responses: List[List[Any]] = Field(
        ..., description=(
            "Binary response matrix (rows=persons, cols=items). May contain headers/labels; "
            "values could be 0/1/None/strings; they will be cleaned server-side."
        )
    )

    @field_validator("responses")
    @classmethod
    def validate_responses(cls, value):
        if not isinstance(value, list) or not value:
            raise ValueError("Javob matritsasi bo'sh bo'lmasligi kerak")
        if not all(isinstance(row, list) for row in value):
            raise ValueError("Har bir qator ro'yxat bo'lishi kerak")
        return value
