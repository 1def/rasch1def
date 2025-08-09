from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ScoreConfig:
    theta_min: float = -3.0
    theta_max: float = 3.0
    score_min: int = 0
    score_max: int = 100
    method: str = "linear"  # or "logistic"

    # Grade thresholds (inclusive lower bounds)
    # e.g., [(90, 'A+'), (80, 'A'), (70, 'B+'), (60, 'B'), (50, 'C+'), (0, 'C')]
    grade_thresholds: Tuple[Tuple[int, str], ...] = (
        (70, "A+"),
        (65, "A"),
        (60, "B+"),
        (55, "B"),
        (50, "C+"),
        (0, "C"),
    )


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def theta_to_score(theta: float, cfg: ScoreConfig = ScoreConfig()) -> int:
    if cfg.method == "logistic":
        import math
        # Center at 0, scale so that [-3, +3] spans roughly [~5, ~95]
        p = 1.0 / (1.0 + math.exp(-theta))
        score = cfg.score_min + p * (cfg.score_max - cfg.score_min)
        return int(round(score))
    # default linear mapping
    t = _clip(theta, cfg.theta_min, cfg.theta_max)
    span = (cfg.theta_max - cfg.theta_min) or 1.0
    norm = (t - cfg.theta_min) / span
    score = cfg.score_min + norm * (cfg.score_max - cfg.score_min)
    return int(round(score))


def assign_grade(score: int, cfg: ScoreConfig = ScoreConfig()) -> str:
    for lower, label in cfg.grade_thresholds:
        if score >= lower:
            return label
    return cfg.grade_thresholds[-1][1]


def enrich_person_scores(result: Dict) -> Dict:
    persons = result.get("persons") or []
    if not isinstance(persons, list):
        return result

    new_persons: List[Dict] = []
    for p in persons:
        theta = p.get("eap")
        if theta is None:
            new_persons.append({**p, "score": None, "grade": None})
            continue
        s = theta_to_score(float(theta))
        g = assign_grade(s)
        new_persons.append({**p, "score": s, "grade": g})

    result = {**result, "persons": new_persons}
    # Optional: include a small summary
    try:
        n_items = int(result.get("fit", {}).get("n_items", 0))
    except Exception:
        n_items = 0
    summary = {
        "num_persons": len(new_persons),
        "num_items": n_items,
        "avg_score": round(
            sum(p["score"] for p in new_persons if isinstance(p.get("score"), int))
            / max(1, sum(1 for p in new_persons if isinstance(p.get("score"), int))),
            2,
        ) if new_persons else 0,
    }
    result["summary"] = summary
    return result
