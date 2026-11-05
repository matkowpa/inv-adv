"""Historia biegów: rozdzielenie scheduled/manual i próg tygodni paper tradingu."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from inv_adv.metrics import compute_metrics, history_weeks
from inv_adv.report import append_history
from inv_adv.review import Snapshot


def make_snapshot(total: float = 100.0, bench: float = 10.0) -> Snapshot:
    positions = pd.DataFrame({
        "ticker": ["A"],
        "quantity": [1.0],
        "asset_class": ["a"],
        "currency": ["PLN"],
        "price": [total],
        "fx_rate": [1.0],
        "value_base": [total],
    })
    return Snapshot(positions=positions, total_value=total, allocation={"a": 1.0},
                    drift_pp={"a": 0.0}, benchmark_value=bench,
                    benchmark_values={"bench": bench}, targets={"a": 1.0})


def weekly_history(values: list[float], run_kind: str = "scheduled") -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=len(values), freq="7D")
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_value": values,
        "benchmark_value": [200.0 + i for i in range(len(values))],
        "run_kind": [run_kind] * len(values),
    })


def test_scheduled_run_is_idempotent_within_iso_week(tmp_path):
    path = tmp_path / "history.csv"
    append_history(make_snapshot(100.0), path, run_kind="scheduled",
                   now=datetime(2026, 11, 2, 10, 0))
    append_history(make_snapshot(101.0), path, run_kind="scheduled",
                   now=datetime(2026, 11, 4, 10, 0))

    df = pd.read_csv(path)
    assert len(df) == 1
    assert df.loc[0, "total_value"] == pytest.approx(101.0)
    assert df.loc[0, "run_kind"] == "scheduled"

    append_history(make_snapshot(102.0), path, run_kind="scheduled",
                   now=datetime(2026, 11, 9, 10, 0))
    assert len(pd.read_csv(path)) == 2


def test_manual_run_does_not_replace_scheduled(tmp_path):
    path = tmp_path / "history.csv"
    append_history(make_snapshot(100.0), path, run_kind="scheduled",
                   now=datetime(2026, 11, 2, 10, 0))
    append_history(make_snapshot(900.0), path, run_kind="manual",
                   now=datetime(2026, 11, 3, 10, 0))

    df = pd.read_csv(path)
    assert len(df) == 2
    assert set(df["run_kind"]) == {"scheduled", "manual"}


def test_metrics_filter_scheduled_only():
    hist = weekly_history([100.0, 110.0, 99.0, 104.5])
    extra = pd.DataFrame({
        "date": ["2026-01-03T10:00:00"],
        "total_value": [500.0],
        "benchmark_value": [250.0],
        "run_kind": ["manual"],
    })
    hist = pd.concat([hist, extra], ignore_index=True)

    m = compute_metrics(hist, run_kinds=("scheduled",))
    assert m is not None
    assert m.n_points == 4
    assert m.n_weeks == 4
    assert m.run_kinds == ("scheduled",)


def test_require_weeks_blocks_until_enough_history():
    hist = weekly_history([100.0, 110.0, 99.0, 104.5])
    assert compute_metrics(hist, require_weeks=5) is None
    assert compute_metrics(hist, require_weeks=4) is not None


def test_legacy_history_is_not_paper_trading():
    hist = weekly_history([100.0, 110.0, 99.0, 104.5])
    hist = hist.drop(columns=["run_kind"])
    assert compute_metrics(hist) is not None
    assert compute_metrics(hist, run_kinds=("scheduled",)) is None
    assert history_weeks(hist, run_kinds=("scheduled",)) == 0
    assert history_weeks(hist) == 4
