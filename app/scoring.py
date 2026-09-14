

from typing import Optional


def clamp(
    value: float,
    low: float = 0.0,
    high: float = 1.0,
) -> float:
    return max(low, min(high, value))


def normalize_sst(
    sst_c: Optional[float],
) -> Optional[float]:
    """
    Global-safe SST normalization.

    IMPORTANT:
    Absolute SST suitability is species-, season-, depth- and
    region-dependent. ORCA does not currently have that context,
    so this function must NOT assume that tropical SST is always
    better than cold-water SST.

    Therefore:
    - valid ocean SST -> neutral 0.50
    - clearly invalid/out-of-range values -> 0.00
    - missing -> None

    SST's directional information is handled separately through
    the SST anomaly/stability component when available.
    """

    if sst_c is None:
        return None

    # Broad physical sanity check for an ocean surface temperature.
    if sst_c < -3.0 or sst_c > 40.0:
        return 0.0

    return 0.50


def normalize_chlorophyll(
    chl: Optional[float],
) -> Optional[float]:
    """
    Global-safe chlorophyll normalization.

    Chlorophyll is treated as an ecosystem/productivity signal,
    NOT as a direct measurement of fish abundance.

    A logarithmic scale is used because chlorophyll values can
    span a much wider range across ocean regions than a simple
    linear 0.05-3.0 mg/m3 scale.
    """

    if chl is None:
        return None

    if chl <= 0:
        return 0.0

    # Approximate broad open/coastal ocean range for a prototype.
    # log10(0.01) ... log10(10) maps to 0 ... 1.
    import math

    value = (
        math.log10(chl) - math.log10(0.01)
    ) / (
        math.log10(10.0) - math.log10(0.01)
    )

    return clamp(value)


def normalize_sst_anomaly(
    anomaly_c: Optional[float],
) -> Optional[float]:
    """
    Convert SST anomaly into a stability score.

    Near-zero anomaly is treated as more stable.
    Large positive/negative anomalies reduce the score.

    Demo heuristic only; it is not a biological suitability model.
    """

    if anomaly_c is None:
        return None

    magnitude = abs(anomaly_c)

    if magnitude <= 0.5:
        return 1.0

    if magnitude >= 2.0:
        return 0.0

    return clamp(
        1.0
        - (
            (magnitude - 0.5)
            / 1.5
        )
    )


def normalize_chlorophyll_anomaly(
    anomaly_mg_m3: Optional[float],
    baseline_mean_mg_m3: Optional[float] = None,
) -> Optional[float]:
    """
    Convert chlorophyll anomaly into an ecosystem-signal score.

    Positive relative change increases the score and negative
    relative change decreases it.

    This is NOT a fish-abundance model.
    """

    if anomaly_mg_m3 is None:
        return None

    if (
        baseline_mean_mg_m3 is not None
        and baseline_mean_mg_m3 > 0
    ):
        relative_change = (
            anomaly_mg_m3
            / baseline_mean_mg_m3
        )

        if relative_change >= 0.50:
            return 1.0

        if relative_change <= -0.50:
            return 0.0

        return clamp(
            (
                relative_change + 0.50
            )
            / 1.00
        )

    if anomaly_mg_m3 >= 0.5:
        return 1.0

    if anomaly_mg_m3 <= -0.5:
        return 0.0

    return clamp(
        (anomaly_mg_m3 + 0.5) / 1.0
    )


def calculate_ocean_score(
    sst_c: Optional[float],
    chlorophyll_mg_m3: Optional[float],
    pfz_score: Optional[float],
    sst_anomaly_c: Optional[float] = None,
    chlorophyll_anomaly_mg_m3: Optional[float] = None,
    chlorophyll_baseline_mg_m3: Optional[float] = None,
) -> Optional[float]:
    """
    Calculate a prototype Ocean Opportunity Score.

    IMPORTANT:
    This is a decision-support heuristic, NOT a validated
    fish-abundance prediction model.

    Global design:
    - Absolute SST is kept neutral because temperature suitability
      depends on species/season/region and ORCA does not yet have
      that context.
    - Chlorophyll provides an ecosystem/productivity signal.
    - SST anomaly measures thermal stability.
    - Chlorophyll anomaly measures recent ecosystem change.
    - INCOIS PFZ is strong evidence where it is available.

    Missing evidence is excluded and the remaining weights are
    re-normalized.
    """

    parts = []

    # 1. Current SST
    sst_norm = normalize_sst(sst_c)

    if sst_norm is not None:
        parts.append((sst_norm, 0.10))

    # 2. Current chlorophyll
    chl_norm = normalize_chlorophyll(
        chlorophyll_mg_m3
    )

    if chl_norm is not None:
        parts.append((chl_norm, 0.20))

    # 3. SST anomaly / stability
    sst_anomaly_norm = normalize_sst_anomaly(
        sst_anomaly_c
    )

    if sst_anomaly_norm is not None:
        parts.append((sst_anomaly_norm, 0.20))

    # 4. Chlorophyll anomaly
    chl_anomaly_norm = normalize_chlorophyll_anomaly(
        chlorophyll_anomaly_mg_m3,
        chlorophyll_baseline_mg_m3,
    )

    if chl_anomaly_norm is not None:
        parts.append((chl_anomaly_norm, 0.20))

    # 5. INCOIS PFZ evidence
    if pfz_score is not None:
        parts.append(
            (clamp(pfz_score), 0.30)
        )

    if not parts:
        return None

    total_weight = sum(
        weight for _, weight in parts
    )

    weighted = sum(
        value * weight
        for value, weight in parts
    )

    return round(
        100.0 * weighted / total_weight,
        1,
    )


def classify_pfz(
    score: Optional[float],
) -> str:
    if score is None:
        return "unknown"

    if score >= 0.75:
        return "favourable"

    if score >= 0.50:
        return "moderate"

    if score >= 0.25:
        return "low"

    return "unfavourable"
