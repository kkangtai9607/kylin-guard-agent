from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TrendResult:
    window: int
    ewma: float
    z_score: float
    slope: float
    anomalous: bool
    basis: str


def analyze_trend(values: list[float], alpha: float = 0.3, z_threshold: float = 2.5) -> TrendResult:
    if len(values) < 3 or not 0 < alpha <= 1:
        raise ValueError("at least three values and valid alpha are required")
    ewma = values[0]
    for value in values[1:]:
        ewma = alpha * value + (1 - alpha) * ewma
    history = values[:-1]
    mean = sum(history) / len(history)
    variance = sum((value - mean) ** 2 for value in history) / len(history)
    deviation = math.sqrt(variance)
    z_score = 0.0 if deviation == 0 else (values[-1] - mean) / deviation
    slope = (values[-1] - values[0]) / (len(values) - 1)
    return TrendResult(
        len(values),
        round(ewma, 4),
        round(z_score, 4),
        round(slope, 4),
        abs(z_score) >= z_threshold,
        f"EWMA alpha={alpha}; Z threshold={z_threshold}",
    )
