from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def run_rasch_model(csv_path: Path) -> dict[str, Any]:
    script_path = (Path(__file__).resolve().parents[1] / "r" / "rasch_calc.R").resolve()

    if not script_path.exists():
        raise RuntimeError(f"R skript topilmadi: {script_path}")
    if not csv_path.exists():
        raise RuntimeError(f"CSV fayl topilmadi: {csv_path}")

    cmd = [
        "Rscript",
        str(script_path),
        str(csv_path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "Rscript topilmadi. Iltimos, R o'rnatilganligini va 'Rscript' tizim PATH ichida ekanligini tekshiring."
        ) from e

    if proc.returncode != 0:
        stderr_msg = (proc.stderr or "").strip()
        raise RuntimeError(f"R hisoblash xatosi. Kod: {proc.returncode}. Xabar: {stderr_msg}")

    stdout_text = (proc.stdout or "").strip()
    if not stdout_text:
        raise RuntimeError("R skript hech qanday natija chiqarmadi")

    try:
        result: dict[str, Any] = json.loads(stdout_text)
    except json.JSONDecodeError as e:
        snippet = stdout_text[:500]
        raise RuntimeError(f"R skript JSON formatida natija qaytarmadi. Boshi: {snippet}") from e

    return result
