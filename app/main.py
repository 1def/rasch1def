from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .schemas import CalculateRequest
from .core.r_runner import run_rasch_model


app = FastAPI(
    title="Rasch Model Calculator",
    version="1.0.0",
    description="FastAPI backend that delegates Rasch model estimation to R (ltm::rasch) and returns JSON results.",
)


def _write_matrix_to_csv(temp_dir: Path, matrix: List[List[Optional[int]]]) -> Path:
    # No header; values separated by commas; missing represented as empty field
    csv_path = temp_dir / "responses.csv"
    with csv_path.open("w", encoding="utf-8") as f:
        for row in matrix:
            row_str = ",".join("" if v is None else str(int(v)) for v in row)
            f.write(row_str + "\n")
    return csv_path


@app.post("/calculate")
def calculate(request: CalculateRequest) -> JSONResponse:
    # Basic validation already performed by Pydantic; enforce rectangular matrix at runtime too
    if not request.responses or not request.responses[0]:
        raise HTTPException(status_code=400, detail="Bo'sh javob matritsasi yuborildi.")

    num_items = len(request.responses[0])
    for idx, row in enumerate(request.responses, start=1):
        if len(row) != num_items:
            raise HTTPException(status_code=400, detail=f"{idx}-qator uzunligi mos emas: {len(row)} != {num_items}")
        for jdx, val in enumerate(row, start=1):
            if val is None:
                continue
            if val not in (0, 1):
                raise HTTPException(status_code=400, detail=f"Yaroqsiz qiymat ({val}) {idx}-qator, {jdx}-ustun uchun. Faqat 0/1 yoki null ruxsat etiladi.")

    with tempfile.TemporaryDirectory(prefix="rasch_") as tmpdir:
        tmp_path = Path(tmpdir)
        csv_path = _write_matrix_to_csv(tmp_path, request.responses)

        try:
            result: dict[str, Any] = run_rasch_model(csv_path)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return JSONResponse(content=result)
