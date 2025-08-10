from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .schemas import CalculateRequest
from .core.cleaning import clean_response_matrix
from .core.r_runner import run_rasch_model
from app.services.scoring import enrich_person_scores


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
    # 1) Tozalash va heuristika asosida header/ustunlarni filtrlash
    cleaned = clean_response_matrix(request.responses)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Tozalashdan so'ng matritsa bo'sh qoldi.")

    # 2) Minimal tekshiruv (hamma qatorlar bir xil uzunlikda bo'lsin)
    num_items = len(cleaned[0])
    if num_items == 0:
        raise HTTPException(status_code=400, detail="Hech qanday item ustuni aniqlanmadi.")
    for idx, row in enumerate(cleaned, start=1):
        if len(row) != num_items:
            raise HTTPException(status_code=400, detail=f"{idx}-qator uzunligi mos emas: {len(row)} != {num_items}")

    with tempfile.TemporaryDirectory(prefix="rasch_") as tmpdir:
        tmp_path = Path(tmpdir)
        csv_path = _write_matrix_to_csv(tmp_path, cleaned)

        try:
            result: dict[str, Any] = run_rasch_model(csv_path)
            result = enrich_person_scores(result)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return JSONResponse(content=result)
