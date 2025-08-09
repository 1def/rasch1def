from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CalculateRequest(BaseModel):
    responses: List[List[Optional[int]]] = Field(
        ..., description="Binary response matrix (rows=persons, cols=items). Values: 0/1 or null for missing."
    )

    @field_validator("responses")
    @classmethod
    def validate_responses(cls, value: List[List[Optional[int]]]) -> List[List[Optional[int]]]:
        if not isinstance(value, list) or not value:
            raise ValueError("Javob matritsasi bo'sh bo'lmasligi kerak")
        row_lengths = {len(row) for row in value}
        if len(row_lengths) != 1:
            raise ValueError("Barcha qatorlar bir xil uzunlikda bo'lishi kerak")
        for row in value:
            for v in row:
                if v is None:
                    continue
                if v not in (0, 1):
                    raise ValueError("Faqat 0/1 yoki null qiymatlar ruxsat etiladi")
        return value
