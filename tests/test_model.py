from pathlib import Path
import math
import pandas as pd
import pytest
from model import Assumptions, validate_airports, evaluate, apply_laf_scenario, make_memo

DATA = Path(__file__).resolve().parents[1] / "data" / "sample_airports.csv"


def sample():
    return pd.read_csv(DATA)


def test_probabilities_sum_to_one_and_passengers_total():
    x = evaluate(sample(), Assumptions(traveler_count=10000))
    assert x.modeled_share.sum() == pytest.approx(1.0)
    assert x.modeled_passengers.sum() == pytest.approx(10000)


def test_lower_laf_fare_raises_modeled_share():
    a = Assumptions()
    before = evaluate(sample(), a)
    after = evaluate(apply_laf_scenario(sample(), fare_change=-75), a)
    b = float(before.loc[before.airport_code == "LAF", "modeled_share"].iloc[0])
    n = float(after.loc[after.airport_code == "LAF", "modeled_share"].iloc[0])
    assert n > b


def test_more_laf_departures_raises_modeled_share():
    a = Assumptions()
    before = evaluate(sample(), a).set_index("airport_code")
    after = evaluate(apply_laf_scenario(sample(), departures_change=20), a).set_index("airport_code")
    assert after.loc["LAF", "modeled_share"] > before.loc["LAF", "modeled_share"]


def test_invalid_negative_data():
    bad = sample()
    bad.loc[0, "roundtrip_fare_usd"] = -10
    with pytest.raises(ValueError, match="negative"):
        validate_airports(bad)


def test_duplicate_codes_rejected():
    bad = sample()
    bad.loc[1, "airport_code"] = "LAF"
    with pytest.raises(ValueError, match="unique"):
        validate_airports(bad)


def test_zero_departures_and_zero_travelers():
    d = sample()
    d["weekly_departures"] = 0
    out = evaluate(d, Assumptions(traveler_count=0))
    assert math.isclose(out.modeled_share.sum(), 1)
    assert out.modeled_passengers.sum() == 0


def test_memo_explicitly_labels_uncertainty():
    a = Assumptions()
    base = evaluate(sample(), a)
    changed = evaluate(apply_laf_scenario(sample(), -30, 10), a)
    memo = make_memo(base, changed, a, -30, 10, 0, 0)
    assert "NOT an actual passenger forecast" in memo
    assert "LAF" in memo
