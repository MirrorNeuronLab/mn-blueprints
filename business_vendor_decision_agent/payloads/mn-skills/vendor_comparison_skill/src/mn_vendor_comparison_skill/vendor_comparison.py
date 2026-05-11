from __future__ import annotations

import re
from typing import Any


def normalize_criteria(criteria: list[str | dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize weighted criteria used to compare vendors."""

    normalized: list[dict[str, Any]] = []
    for item in criteria:
        if isinstance(item, str):
            data = {"name": item, "weight": 1.0, "higher_is_better": True}
        else:
            data = dict(item)
        name = _clean(data.get("name") or data.get("criterion"))
        if not name:
            raise ValueError("criterion name is required")
        normalized.append(
            {
                "name": name,
                "weight": float(data.get("weight", 1.0)),
                "higher_is_better": bool(data.get("higher_is_better", True)),
            }
        )
    return normalized


def score_vendors(
    vendors: list[dict[str, Any]],
    criteria: list[str | dict[str, Any]],
    *,
    score_key: str = "scores",
) -> list[dict[str, Any]]:
    """Score vendors with weighted criteria on a common 0-5 scale."""

    normalized_criteria = normalize_criteria(criteria)
    total_weight = sum(max(criterion["weight"], 0.0) for criterion in normalized_criteria) or 1.0
    scored: list[dict[str, Any]] = []
    for vendor in vendors:
        score_breakdown: list[dict[str, Any]] = []
        total = 0.0
        raw_scores = vendor.get(score_key, {})
        for criterion in normalized_criteria:
            raw_score = _score_for_criterion(vendor, raw_scores, criterion["name"])
            normalized_score = max(0.0, min(5.0, raw_score))
            if not criterion["higher_is_better"]:
                normalized_score = 5.0 - normalized_score
            weighted = normalized_score * criterion["weight"]
            total += weighted
            score_breakdown.append(
                {
                    "criterion": criterion["name"],
                    "score": round(normalized_score, 2),
                    "weight": criterion["weight"],
                    "weighted_score": round(weighted, 2),
                }
            )
        scored.append(
            {
                "vendor": _clean(vendor.get("name") or vendor.get("vendor") or "Unnamed vendor"),
                "weighted_score": round(total / total_weight, 2),
                "scores": score_breakdown,
                "notes": _clean(vendor.get("notes") or ""),
            }
        )
    return sorted(scored, key=lambda item: item["weighted_score"], reverse=True)


def build_comparison_matrix(vendors: list[dict[str, Any]], criteria: list[str | dict[str, Any]]) -> dict[str, Any]:
    """Build a matrix view plus weighted ranking for vendor comparison."""

    normalized_criteria = normalize_criteria(criteria)
    scored = score_vendors(vendors, normalized_criteria)
    rows = []
    for vendor in vendors:
        scores = vendor.get("scores", {})
        row = {"vendor": _clean(vendor.get("name") or vendor.get("vendor") or "Unnamed vendor")}
        for criterion in normalized_criteria:
            row[criterion["name"]] = _score_for_criterion(vendor, scores, criterion["name"])
        rows.append(row)
    return {"criteria": normalized_criteria, "rows": rows, "ranking": scored}


def recommend_vendor(scored_vendors: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a recommendation summary from scored vendors."""

    if not scored_vendors:
        return {"recommended": "", "rationale": "No vendors were provided.", "confidence": "low"}
    best = scored_vendors[0]
    runner_up = scored_vendors[1] if len(scored_vendors) > 1 else None
    margin = best["weighted_score"] - (runner_up["weighted_score"] if runner_up else 0.0)
    confidence = "high" if margin >= 0.75 else "medium" if margin >= 0.25 else "low"
    return {
        "recommended": best["vendor"],
        "rationale": f"{best['vendor']} has the highest weighted score ({best['weighted_score']}).",
        "confidence": confidence,
        "margin": round(margin, 2),
    }


def _score_for_criterion(vendor: dict[str, Any], scores: dict[str, Any], criterion_name: str) -> float:
    raw = scores.get(criterion_name)
    if raw is None:
        normalized_name = _slug(criterion_name)
        raw = scores.get(normalized_name, vendor.get(criterion_name, vendor.get(normalized_name, 0)))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
