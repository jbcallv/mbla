from collections import Counter

import numpy as np
from scipy.stats import binomtest


def cluster_means(frame, value, cluster):
    grouped = frame.dropna(subset=[value]).groupby(cluster)[value]
    return grouped.sum().to_numpy(dtype=float), grouped.count().to_numpy(dtype=float)


def cluster_bootstrap_ci(frame, value, cluster="template", resamples=10000, seed=0, level=0.95):
    sums, counts = cluster_means(frame, value, cluster)
    if counts.sum() == 0:
        return None, None, None
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(sums), size=(resamples, len(sums)))
    estimates = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)
    tail = (1 - level) / 2
    return sums.sum() / counts.sum(), float(np.quantile(estimates, tail)), float(np.quantile(estimates, 1 - tail))


def paired_difference(frame_a, frame_b, value, cluster="template", resamples=10000, seed=0, level=0.95):
    paired = frame_a[["item", cluster, value]].merge(frame_b[["item", value]], on="item", suffixes=("_a", "_b"))
    paired["difference"] = paired[f"{value}_a"] - paired[f"{value}_b"]
    estimate, low, high = cluster_bootstrap_ci(paired, "difference", cluster, resamples, seed, level)
    return {"difference": estimate, "low": low, "high": high, "p": bootstrap_p_value(paired, cluster, resamples, seed)}


def bootstrap_p_value(paired, cluster, resamples, seed):
    sums, counts = cluster_means(paired, "difference", cluster)
    if counts.sum() == 0:
        return None
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(sums), size=(resamples, len(sums)))
    estimates = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)
    return float(min(1.0, 2 * min((estimates <= 0).mean(), (estimates >= 0).mean())))


def mcnemar_exact(successes_a, successes_b):
    only_a = sum(1 for a, b in zip(successes_a, successes_b) if a and not b)
    only_b = sum(1 for a, b in zip(successes_a, successes_b) if b and not a)
    if only_a + only_b == 0:
        return 1.0
    return binomtest(only_a, only_a + only_b, 0.5).pvalue


def holm(p_values):
    order = sorted(range(len(p_values)), key=lambda index: p_values[index])
    adjusted = [0.0] * len(p_values)
    running_max = 0.0
    for rank, index in enumerate(order):
        running_max = max(running_max, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = running_max
    return adjusted


def cohen_kappa(labels_a, labels_b):
    categories = sorted(set(labels_a) | set(labels_b))
    total = len(labels_a)
    observed = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / total
    expected = sum((labels_a.count(category) / total) * (labels_b.count(category) / total) for category in categories)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def krippendorff_alpha_nominal(units):
    coincidences = Counter()
    for labels in units:
        if len(labels) < 2:
            continue
        for first_index, first in enumerate(labels):
            for second_index, second in enumerate(labels):
                if first_index != second_index:
                    coincidences[(first, second)] += 1 / (len(labels) - 1)
    totals = Counter()
    for (first, _), weight in coincidences.items():
        totals[first] += weight
    pairable = sum(totals.values())
    observed = sum(weight for (first, second), weight in coincidences.items() if first != second)
    expected = sum(totals[first] * totals[second] for first in totals for second in totals if first != second) / (pairable - 1)
    return 1.0 if expected == 0 else 1 - observed / expected


def cluster_bootstrap_interval(groups, statistic, resamples=10000, seed=0, level=0.95):
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(resamples):
        picked = rng.integers(0, len(groups), size=len(groups))
        estimates.append(statistic([row for index in picked for row in groups[index]]))
    tail = (1 - level) / 2
    return float(np.quantile(estimates, tail)), float(np.quantile(estimates, 1 - tail))
