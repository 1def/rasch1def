from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence, Tuple

# ---------- Normalization ----------

def _normalize_cell(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int,)):
        return value if value in (0, 1) else None
    # floats like 1.0 / 0.0
    if isinstance(value, float):
        try:
            iv = int(value)
            return iv if iv in (0, 1) else None
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return None
        low = s.lower()
        # NA tokens
        if low in {"na", "null", "none", "nan", "bo'sh", "bosh"}:
            return None
        # truthy/falsy tokens
        if low in {"1", "true", "t", "yes", "y", "x", "✓", "+"}:
            return 1
        if low in {"0", "false", "f", "no", "n", "-"}:
            return 0
        # numeric string fallback
        try:
            fv = float(s)
            iv = int(fv)
            return iv if iv in (0, 1) else None
        except Exception:
            return None
    # other types -> try int
    try:
        iv = int(value)  # type: ignore[arg-type]
        return iv if iv in (0, 1) else None
    except Exception:
        return None


# ---------- Heuristics for column roles ----------

HEADER_LABEL_TOKENS = {
    # uz/ru/en common tokens that indicate person columns
    "ism", "fam", "familya", "familiya", "talabgor", "o'quvchi", "oquvchi",
    "fio", "name", "first", "last", "surname", "student", "id", "passport",
}

QUESTION_HEADER_PATTERNS = [
    re.compile(r"^q\s*\d+$", re.I),
    re.compile(r"^savol\s*\d+$", re.I),
    re.compile(r"^s\s*\d+$", re.I),
    re.compile(r"^item\s*\d+$", re.I),
    re.compile(r"^(q_|s_|savol_|item_)?\d+$", re.I),
]


def _looks_like_question_header(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    for rx in QUESTION_HEADER_PATTERNS:
        if rx.match(t):
            return True
    return False


def _looks_like_label_header(text: str) -> bool:
    t = re.sub(r"\W+", " ", text.strip().lower())
    if not t:
        return False
    return any(tok in t.split() for tok in HEADER_LABEL_TOKENS)


def _binary_ratio(values: Sequence[Optional[int]]) -> float:
    non_missing = [v for v in values if v is not None]
    if not non_missing:
        return 0.0
    bin_count = sum(1 for v in non_missing if v in (0, 1))
    return bin_count / len(non_missing)


def _pick_best_block(candidate_cols: List[int], target_min: int = 35, target_max: int = 55) -> List[int]:
    if not candidate_cols:
        return []
    # form contiguous blocks
    blocks: List[List[int]] = []
    cur: List[int] = [candidate_cols[0]]
    for j in candidate_cols[1:]:
        if j == cur[-1] + 1:
            cur.append(j)
        else:
            blocks.append(cur)
            cur = [j]
    blocks.append(cur)
    # prefer block within [target_min, target_max]
    def score(block: List[int]) -> Tuple[int, int]:
        ln = len(block)
        # primary: distance from range
        if ln < target_min:
            dist = target_min - ln
        elif ln > target_max:
            dist = ln - target_max
        else:
            dist = 0
        # secondary: longer is better
        return (dist, -ln)
    blocks.sort(key=score)
    best = blocks[0]
    # trim if longer than max
    if len(best) > target_max:
        best = best[:target_max]
    # extend if shorter by merging neighbors (simple)
    return best


def infer_question_columns(rows: List[List[Any]], min_binary_ratio: float = 0.85) -> List[int]:
    if not rows:
        return []
    # ensure rectangular snapshot for detection
    max_len = max(len(r) for r in rows)
    padded = [r + [None] * (max_len - len(r)) for r in rows]

    header = padded[0]
    col_count = len(header)

    # Normalize grid
    norm_grid: List[List[Optional[int]]] = [[_normalize_cell(v) for v in r] for r in padded]

    label_by_header = [False] * col_count
    question_by_header = [False] * col_count

    # header heuristics
    for j, hv in enumerate(header):
        if isinstance(hv, str):
            if _looks_like_label_header(hv):
                label_by_header[j] = True
            if _looks_like_question_header(hv):
                question_by_header[j] = True

    # ratios
    ratios = [_binary_ratio([row[j] for row in norm_grid[1:]]) for j in range(col_count)]

    candidate_cols: List[int] = []
    for j in range(col_count):
        if label_by_header[j]:
            continue
        if question_by_header[j]:
            candidate_cols.append(j)
            continue
        if ratios[j] >= min_binary_ratio:
            candidate_cols.append(j)

    if not candidate_cols:
        # fallback: pick columns with ratio >= 0.7
        candidate_cols = [j for j in range(col_count) if ratios[j] >= 0.7]

    # Choose best contiguous block around typical count (35-55)
    candidate_cols.sort()
    picked = _pick_best_block(candidate_cols)

    # if still empty, fallback to all with max ratio top-N (e.g., 40)
    if not picked:
        by_ratio = sorted(range(col_count), key=lambda j: ratios[j], reverse=True)
        picked = by_ratio[:40]
        picked.sort()

    return picked


def clean_response_matrix(
    matrix: List[List[Any]],
    fill_missing: Optional[int] = None,
) -> List[List[Optional[int]]]:
    if not matrix:
        return []

    # drop completely empty rows early
    raw = [list(row) for row in matrix if any(str(c).strip() for c in row)]
    if not raw:
        return []

    # infer question columns
    qcols = infer_question_columns(raw)

    # Normalize and select only question columns
    cleaned: List[List[Optional[int]]] = []
    for row in raw:
        norm_row = [_normalize_cell(v) for v in row]
        # pad
        if len(norm_row) < (max(qcols) + 1 if qcols else 0):
            norm_row += [None] * ((max(qcols) + 1) - len(norm_row))
        selected = [norm_row[j] for j in qcols] if qcols else norm_row
        cleaned.append(selected)

    # drop rows with no 0/1
    cleaned = [r for r in cleaned if any(v in (0, 1) for v in r)]

    # optional fill
    if fill_missing in (0, 1):
        cleaned = [[(fill_missing if v is None else v) for v in r] for r in cleaned]

    return cleaned
