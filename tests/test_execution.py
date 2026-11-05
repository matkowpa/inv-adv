"""M3b — log faktycznych wykonań (fill)."""
from datetime import datetime

import pandas as pd
import pytest

from inv_adv.execution import FIELDS, record_execution


def test_record_execution_appends_monthly_fill(tmp_path):
    path = record_execution("sxr8.de", "buy", 10, 520.5, fee=2.6,
                            note="IBKR fill", executed_at=datetime(2026, 11, 5, 10, 30),
                            out_dir=tmp_path)
    assert path.name == "2026-11.csv"
    df = pd.read_csv(path)
    assert list(df.columns) == FIELDS
    assert len(df) == 1
    row = df.iloc[0]
    assert row["ticker"] == "SXR8.DE"
    assert row["side"] == "BUY"
    assert row["quantity"] == 10
    assert row["price"] == 520.5
    assert row["fee"] == 2.6

    record_execution("SXR8.DE", "SELL", 5, 530, executed_at=datetime(2026, 11, 6),
                     out_dir=tmp_path)
    assert len(pd.read_csv(path)) == 2


def test_record_execution_validates(tmp_path):
    with pytest.raises(ValueError):
        record_execution("X", "HOLD", 1, 1, out_dir=tmp_path)
    with pytest.raises(ValueError):
        record_execution("X", "BUY", 0, 1, out_dir=tmp_path)
    with pytest.raises(ValueError):
        record_execution("X", "BUY", 1, 1, fee=-1, out_dir=tmp_path)
