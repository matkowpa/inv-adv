"""Import portfela z eksportu IBKR (.xlsx) do data/portfolio.csv.

Użycie:
    python -m inv_adv.import_ibkr data/portfel_2026.09.01.xlsx

Wymaga mapowania pozycji w data/ibkr_mapping.yaml (klucz: "Symbol|Waluta").
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

from inv_adv.data import load_config

MAPPING_PATH = Path("data/ibkr_mapping.yaml")
PORTFOLIO_OUT = Path("data/portfolio.csv")
REQUIRED_COLUMNS = ["Currency", "Symbol", "Description", "Quantity"]


def load_mapping(path: Path = MAPPING_PATH) -> dict:
    """Mapowanie z walidacją struktury wpisów."""
    with open(path, encoding="utf-8") as f:
        mapping = yaml.safe_load(f) or {}
    for key, val in mapping.items():
        if "yahoo" not in val or "asset_class" not in val:
            raise ValueError(f"{path}: wpis '{key}' wymaga pól 'yahoo' i 'asset_class'")
    return mapping


def import_ibkr(xlsx_path: Path, mapping: dict, cfg: dict,
                out_path: Path = PORTFOLIO_OUT) -> pd.DataFrame:
    """Konwertuje eksport IBKR na format data/portfolio.csv.

    Waliduje: kolumny eksportu, mapowanie każdej pozycji (Symbol|Waluta)
    i klasy aktywów vs config.yaml targets. Zwraca gotowy DataFrame.
    """
    df = pd.read_excel(xlsx_path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{xlsx_path}: brak kolumn {missing}")

    rows, unmapped = [], []
    for _, r in df.iterrows():
        key = f"{r['Symbol']}|{str(r['Currency']).upper()}"
        entry = mapping.get(key)
        if entry is None:
            unmapped.append(key)
            continue
        if entry["asset_class"] not in cfg["targets"]:
            raise ValueError(f"{key}: klasa '{entry['asset_class']}' "
                             f"nie istnieje w config.yaml targets")
        rows.append({
            "ticker": entry["yahoo"],
            "quantity": float(r["Quantity"]),
            "asset_class": entry["asset_class"],
            "currency": str(r["Currency"]).upper(),
        })
    if unmapped:
        raise ValueError(f"brak mapowania (dodaj do {MAPPING_PATH}): {sorted(unmapped)}")

    out = pd.DataFrame(rows).sort_values("ticker").reset_index(drop=True)
    out.to_csv(out_path, index=False)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import portfela z eksportu IBKR (.xlsx)")
    parser.add_argument("xlsx", help="eksport IBKR, np. data/portfel_2026.09.01.xlsx")
    parser.add_argument("--mapping", default=str(MAPPING_PATH))
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--out", default=str(PORTFOLIO_OUT))
    args = parser.parse_args(argv)

    mapping = load_mapping(Path(args.mapping))
    cfg = load_config(Path(args.config))
    out = import_ibkr(Path(args.xlsx), mapping, cfg, Path(args.out))
    print(f"Zaimportowano {len(out)} pozycji -> {args.out}")
    print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
