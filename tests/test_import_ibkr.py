"""Importer IBKR — mapowanie, walidacja, CSV (offline, fixture xlsx)."""
import pandas as pd
import pytest

from inv_adv.import_ibkr import import_ibkr, load_mapping

CFG = {"targets": {"equity_us": 0.5, "crypto": 0.5}}


def make_xlsx(tmp_path):
    df = pd.DataFrame({
        "Currency": ["EUR", "EUR"],
        "Symbol": ["SXR8", "BITC"],
        "Description": ["ISHARES CORE S&P 500", "COINSHARES BITCOIN ETP"],
        "Quantity": [1, 2],
        "Cost Price": [700.0, 64.0],
        "Cost Basis": [700.0, 128.0],
        "Close Price": [714.0, 64.1],
        "Value": [714.0, 128.2],
    })
    path = tmp_path / "portfel_test.xlsx"
    df.to_excel(path, index=False)
    return path


def make_mapping():
    return {
        "SXR8|EUR": {"yahoo": "SXR8.DE", "asset_class": "equity_us"},
        "BITC|EUR": {"yahoo": "BITC.AS", "asset_class": "crypto"},
    }


def test_import_writes_csv(tmp_path):
    path = make_xlsx(tmp_path)
    out = import_ibkr(path, make_mapping(), CFG, tmp_path / "portfolio.csv")
    assert len(out) == 2
    assert set(out["ticker"]) == {"SXR8.DE", "BITC.AS"}
    assert out.loc[out["ticker"] == "BITC.AS", "quantity"].iloc[0] == 2.0
    saved = pd.read_csv(tmp_path / "portfolio.csv")
    assert len(saved) == 2


def test_unmapped_symbol_raises(tmp_path):
    path = make_xlsx(tmp_path)
    mapping = {"SXR8|EUR": {"yahoo": "SXR8.DE", "asset_class": "equity_us"}}
    with pytest.raises(ValueError, match="BITC\\|EUR"):
        import_ibkr(path, mapping, CFG, tmp_path / "portfolio.csv")


def test_unknown_asset_class_raises(tmp_path):
    path = make_xlsx(tmp_path)
    mapping = {
        "SXR8|EUR": {"yahoo": "SXR8.DE", "asset_class": "equity_us"},
        "BITC|EUR": {"yahoo": "BITC.AS", "asset_class": "bonds"},
    }
    with pytest.raises(ValueError, match="bonds"):
        import_ibkr(path, mapping, CFG, tmp_path / "portfolio.csv")


def test_load_mapping_real_file():
    mapping = load_mapping()
    assert len(mapping) >= 14
    for val in mapping.values():
        assert "yahoo" in val and "asset_class" in val
