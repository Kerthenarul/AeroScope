"""Transparent illustrative airport-choice model, not a calibrated demand forecast."""
from __future__ import annotations
import math
from dataclasses import dataclass
import pandas as pd

REQUIRED_COLUMNS = (
    "airport_code", "airport_name", "roundtrip_fare_usd", "drive_time_min",
    "weekly_departures", "parking_cost_usd", "connection_penalty_min",
)


@dataclass(frozen=True)
class Assumptions:
    traveler_count: int = 10000
    value_of_time_usd_per_hour: float = 25.0
    fare_weight: float = 1.0
    parking_weight: float = 1.0
    frequency_preference: float = 1.4
    price_sensitivity_usd: float = 65.0
    trip_duration_days: int = 4
    roundtrip_drive: bool = True


def validate_airports(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a clean copy or raise ValueError with a friendly explanation."""
    missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    df = frame.loc[:, REQUIRED_COLUMNS].copy()
    if df.empty:
        raise ValueError("Provide at least one airport.")
    df["airport_code"] = df["airport_code"].astype(str).str.strip().str.upper()
    df["airport_name"] = df["airport_name"].astype(str).str.strip()
    if df["airport_code"].eq("").any() or df["airport_name"].eq("").any():
        raise ValueError("Airport codes and names cannot be blank.")
    if df["airport_code"].duplicated().any():
        raise ValueError("Each airport_code must be unique.")
    for col in REQUIRED_COLUMNS[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if not df[col].map(math.isfinite).all():
            raise ValueError(f"Column '{col}' must contain finite numeric values.")
        if (df[col] < 0).any():
            raise ValueError(f"Column '{col}' cannot be negative.")
    if len(df) > 30:
        raise ValueError("Use 30 or fewer airports for the interactive simulator.")
    return df.reset_index(drop=True)


def evaluate(df: pd.DataFrame, assumptions: Assumptions) -> pd.DataFrame:
    """Compute generalized costs and hypothetical choice shares via softmax.

    This is an explanatory toy model, not fit to observed passenger behavior.
    """
    df = validate_airports(df)
    if assumptions.traveler_count < 0 or assumptions.price_sensitivity_usd <= 0:
        raise ValueError("Travelers must be nonnegative and price sensitivity positive.")
    if assumptions.trip_duration_days < 0:
        raise ValueError("Trip duration must be nonnegative.")
    for key in ("value_of_time_usd_per_hour", "fare_weight", "parking_weight", "frequency_preference"):
        if getattr(assumptions, key) < 0:
            raise ValueError(f"{key} must be nonnegative.")
    out = df.copy()
    drive_multiplier = 2 if assumptions.roundtrip_drive else 1
    out["drive_cost_usd"] = (
        out["drive_time_min"] * drive_multiplier / 60 * assumptions.value_of_time_usd_per_hour
    )
    out["connection_cost_usd"] = (
        out["connection_penalty_min"] / 60 * assumptions.value_of_time_usd_per_hour
    )
    out["parking_total_usd"] = out["parking_cost_usd"] * assumptions.trip_duration_days
    out["generalized_cost_usd"] = (
        assumptions.fare_weight * out["roundtrip_fare_usd"]
        + out["drive_cost_usd"]
        + out["connection_cost_usd"]
        + assumptions.parking_weight * out["parking_total_usd"]
    )
    # Frequency bonus is a diminishing-return convenience proxy.
    out["utility"] = (
        -out["generalized_cost_usd"] / assumptions.price_sensitivity_usd
        + assumptions.frequency_preference * out["weekly_departures"].map(math.log1p)
    )
    # Numerically stable softmax.
    w = (out["utility"] - out["utility"].max()).map(math.exp)
    out["modeled_share"] = w / w.sum()
    out["modeled_passengers"] = out["modeled_share"] * assumptions.traveler_count
    return out


def apply_laf_scenario(df: pd.DataFrame, fare_change: float = 0.0, departures_change: int = 0,
                       drive_change: int = 0, parking_change: float = 0.0) -> pd.DataFrame:
    out = validate_airports(df)
    if "LAF" not in set(out["airport_code"]):
        raise ValueError("The LAF scenario requires a row with airport_code=LAF.")
    mask = out["airport_code"] == "LAF"
    for col, change in (
        ("roundtrip_fare_usd", fare_change),
        ("weekly_departures", departures_change),
        ("drive_time_min", drive_change),
        ("parking_cost_usd", parking_change),
    ):
        out.loc[mask, col] = (out.loc[mask, col] + change).clip(lower=0)
    return validate_airports(out)


def make_memo(baseline: pd.DataFrame, scenario: pd.DataFrame, assumptions: Assumptions,
              fare_change: float, departures_change: int, drive_change: int,
              parking_change: float) -> str:
    before = baseline.set_index("airport_code")
    after = scenario.set_index("airport_code")
    old = float(before.loc["LAF", "modeled_share"])
    new = float(after.loc["LAF", "modeled_share"])
    change = (new - old) * assumptions.traveler_count
    return f"""# AeroScope | LAF Airport Scenario Memo

**Analysis type:** Illustrative scenario analysis — NOT an actual passenger forecast.  
**Data:** User-provided or synthetic sample airport attributes.  
**Model:** Uncalibrated multinomial logit (softmax) with generalized travel cost and a frequency proxy.

## Decision question
How might adjustments to LAF's pricing, flight supply, access time, and parking assumptions alter modeled airport choice relative to other airports in the dataset?

## Scenario adjustments (relative to input assumptions)
- LAF roundtrip airfare change: **${fare_change:+.0f}**
- Weekly departure change: **{departures_change:+d}**
- One-way driving time change: **{drive_change:+d} minutes**
- Daily parking price change: **${parking_change:+.0f}**

## Illustrative model results
- LAF baseline modeled share: **{old:.1%}**
- LAF scenario modeled share: **{new:.1%}**
- Change: **{(new-old)*100:+.2f} percentage points**
- Modeled change over **{assumptions.traveler_count:,} hypothetical travelers**: **{change:+,.0f}**

## Recommendation to investigate
Validate the attractiveness of the scenario with observed survey responses, published route schedules, fare observations, and origin-and-destination market data. Investigate operational feasibility, airline economics, and costs before recommending implementation.

## Important limitations
- **Not measured leakage or a traffic forecast.** No choice-model coefficients were estimated from observed passengers.
- This illustrative airport set does not represent all destinations, itinerary patterns, or passenger segments.
- The 'travelers' count is a user-defined hypothetical addressable market, not verified LAF-area demand.
- Revenue and profit effects require separate airline and airport cost/revenue models; the modeled traveler change is not incremental profit.
- To make investment-grade recommendations, fit and validate the model with observed airport-choice data and uncertainty intervals.

Generated by AeroScope. Model parameters: value of time ${assumptions.value_of_time_usd_per_hour:.2f}/hour; fare weight {assumptions.fare_weight:.2f}; parking weight {assumptions.parking_weight:.2f}; frequency preference {assumptions.frequency_preference:.2f}; price sensitivity ${assumptions.price_sensitivity_usd:.2f}; parking {assumptions.trip_duration_days} days; roundtrip drive {assumptions.roundtrip_drive}.
"""
