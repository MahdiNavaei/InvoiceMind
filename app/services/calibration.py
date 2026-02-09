from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass
class IsotonicCalibrator:
    thresholds: list[float]
    values: list[float]

    def predict(self, score: float) -> float:
        if not self.thresholds:
            return _clip(score)
        for idx, threshold in enumerate(self.thresholds):
            if score <= threshold:
                return _clip(self.values[idx])
        return _clip(self.values[-1])


@dataclass
class PlattScaler:
    a: float
    b: float

    def predict(self, score: float) -> float:
        z = (self.a * score) + self.b
        if z >= 0:
            ez = math.exp(-z)
            return 1.0 / (1.0 + ez)
        ez = math.exp(z)
        return ez / (1.0 + ez)


def fit_isotonic(scores: Iterable[float], labels: Iterable[int]) -> IsotonicCalibrator:
    pairs = sorted((float(s), int(y)) for s, y in zip(scores, labels, strict=False))
    if not pairs:
        return IsotonicCalibrator([], [])

    blocks: list[dict[str, float]] = []
    for score, label in pairs:
        block = {"sum": float(label), "count": 1.0, "min_score": score, "max_score": score}
        blocks.append(block)
        while len(blocks) >= 2:
            prev = blocks[-2]
            curr = blocks[-1]
            if (prev["sum"] / prev["count"]) <= (curr["sum"] / curr["count"]):
                break
            merged = {
                "sum": prev["sum"] + curr["sum"],
                "count": prev["count"] + curr["count"],
                "min_score": prev["min_score"],
                "max_score": curr["max_score"],
            }
            blocks = blocks[:-2] + [merged]

    thresholds = [block["max_score"] for block in blocks]
    values = [block["sum"] / block["count"] for block in blocks]
    return IsotonicCalibrator(thresholds=thresholds, values=values)


def fit_platt_scaler(
    scores: Iterable[float],
    labels: Iterable[int],
    *,
    learning_rate: float = 0.1,
    epochs: int = 500,
) -> PlattScaler:
    xs = [float(v) for v in scores]
    ys = [float(v) for v in labels]
    if not xs:
        return PlattScaler(a=1.0, b=0.0)

    a = 1.0
    b = 0.0
    n = len(xs)
    for _ in range(max(1, epochs)):
        grad_a = 0.0
        grad_b = 0.0
        for x, y in zip(xs, ys, strict=False):
            p = _sigmoid((a * x) + b)
            grad_a += (p - y) * x
            grad_b += (p - y)
        grad_a /= n
        grad_b /= n
        a -= learning_rate * grad_a
        b -= learning_rate * grad_b
    return PlattScaler(a=a, b=b)


def expected_calibration_error(probs: Iterable[float], labels: Iterable[int], *, bins: int = 10) -> float:
    p = [float(v) for v in probs]
    y = [int(v) for v in labels]
    if not p:
        return 0.0
    bins = max(1, bins)
    total = len(p)
    ece = 0.0
    for idx in range(bins):
        low = idx / bins
        high = (idx + 1) / bins
        selected = [i for i, prob in enumerate(p) if (low <= prob < high) or (idx == bins - 1 and prob == 1.0)]
        if not selected:
            continue
        conf = sum(p[i] for i in selected) / len(selected)
        acc = sum(y[i] for i in selected) / len(selected)
        ece += (len(selected) / total) * abs(acc - conf)
    return float(ece)


def brier_score(probs: Iterable[float], labels: Iterable[int]) -> float:
    p = [float(v) for v in probs]
    y = [float(v) for v in labels]
    if not p:
        return 0.0
    return sum((pred - actual) ** 2 for pred, actual in zip(p, y, strict=False)) / len(p)


def sweep_risk_threshold(
    *,
    risks: Iterable[float],
    critical_error_labels: Iterable[int],
    critical_false_accept_ceiling: float,
    thresholds: Iterable[float] | None = None,
) -> dict[str, float]:
    risk_values = [float(v) for v in risks]
    labels = [int(v) for v in critical_error_labels]
    if not risk_values:
        return {"threshold": 0.0, "review_ratio": 0.0, "critical_false_accept_rate": 0.0}

    sweep_values = list(thresholds or [i / 100 for i in range(5, 96, 5)])
    best = None
    for threshold in sweep_values:
        needs_review = [1 if risk > threshold else 0 for risk in risk_values]
        review_ratio = sum(needs_review) / len(needs_review)
        false_accept = sum(
            1
            for nr, label in zip(needs_review, labels, strict=False)
            if nr == 0 and label == 1
        )
        cf_rate = false_accept / len(labels)
        candidate = {
            "threshold": float(threshold),
            "review_ratio": float(review_ratio),
            "critical_false_accept_rate": float(cf_rate),
        }
        if cf_rate > critical_false_accept_ceiling:
            continue
        if best is None or candidate["review_ratio"] < best["review_ratio"]:
            best = candidate
    if best is None:
        best = {
            "threshold": min(sweep_values),
            "review_ratio": 1.0,
            "critical_false_accept_rate": 0.0,
        }
    return best


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _clip(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
