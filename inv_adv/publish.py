"""Lokalny dashboard HTML z wynikami portfela (pełne dane).

Uwaga: wygenerowany plik zawiera pełne dane pozycyjne i kwoty — służy
wyłącznie do przeglądania lokalnego. NIE publikować w internecie
(`site/` jest w .gitignore; strona jest samowystarczalna, zero zasobów sieciowych).

Użycie:
    python -m inv_adv.publish
"""
from __future__ import annotations

import argparse
import datetime as dt
from html import escape
from pathlib import Path

import pandas as pd

from inv_adv.data import collect_tickers, fetch_prices, load_config, load_portfolio
from inv_adv.history_rebuild import (build_series, collect_history_tickers,
                                     fetch_history_prices)
from inv_adv.metrics import compute_metrics
from inv_adv.review import build_snapshot

SITE_PATH = Path("site/index.html")


def _svg_chart(dates: list[str], series: dict[str, list[float]],
               width: int = 960, height: int = 340) -> str:
    """Wykres liniowy base-100 jako inline SVG (bez zależności, działa offline)."""
    if not dates or any(len(s) != len(dates) for s in series.values()):
        return "<p>brak danych do wykresu</p>"
    norm = {name: [v / s[0] * 100.0 if s[0] else 0.0 for v in s]
            for name, s in series.items()}
    all_vals = [v for s in norm.values() for v in s]
    lo, hi = min(all_vals), max(all_vals)
    pad = (hi - lo) * 0.06 or 1.0
    lo, hi = lo - pad, hi + pad
    ml, mr, mt, mb = 64.0, 16.0, 16.0, 34.0
    n = len(dates)

    def X(i: int) -> float:
        return ml + (width - ml - mr) * (i / max(n - 1, 1))

    def Y(v: float) -> float:
        return mt + (height - mt - mb) * (1.0 - (v - lo) / (hi - lo))

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
             f'xmlns="http://www.w3.org/2000/svg">']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = Y(v)
        parts.append(f'<line x1="{ml:.0f}" y1="{y:.1f}" x2="{width - mr:.0f}" '
                     f'y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="{ml - 6:.0f}" y="{y + 4:.1f}" text-anchor="end" '
                     f'font-size="11" fill="#6b7280">{v:.0f}</text>')
    for i in (0, n // 2, n - 1):
        parts.append(f'<text x="{X(i):.1f}" y="{height - 10:.0f}" text-anchor="middle" '
                     f'font-size="11" fill="#6b7280">{escape(dates[i][:10])}</text>')
    colors = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"]
    for (name, vals), color in zip(norm.items(), colors):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" '
                     f'points="{pts}"/>')
    lx = ml
    for (name, _), color in zip(norm.items(), colors):
        parts.append(f'<rect x="{lx:.0f}" y="{height - mb + 6:.0f}" width="12" '
                     f'height="12" fill="{color}" rx="2"/>')
        parts.append(f'<text x="{lx + 16:.0f}" y="{height - mb + 16:.0f}" '
                     f'font-size="12" fill="#111827">{escape(name)}</text>')
        lx += 24 + 7.2 * len(name)
    parts.append("</svg>")
    return "".join(parts)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
                   for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def build_page(cfg: dict, portfolio: pd.DataFrame, prices: pd.DataFrame,
               series: pd.DataFrame, generated: str) -> str:
    """Pełny HTML dashboardu z podanych danych (bez dostępu do sieci)."""
    snap = build_snapshot(portfolio, prices, cfg)
    base = str(cfg["base_currency"])
    m = compute_metrics(series, risk_free_annual=float(cfg.get("risk_free_annual", 0.0)))

    dates = series["date"].astype(str).tolist()
    chart = _svg_chart(dates, {
        "Portfel": series["total_value"].astype(float).tolist(),
        "S&P 500 (PLN)": series["benchmark_value"].astype(float).tolist(),
    })

    if m is None:
        metrics_html = "<p>za mało danych</p>"
    else:
        def cell(x: float | None, kind: str) -> str:
            if x is None:
                return "n/d"
            return f"{x:+.2f}" if kind == "sharpe" else f"{x:+.1%}"

        rf = m.risk_free_annual
        rows = [
            ["wynik okresu", cell(m.portfolio.total_return, "pct"),
             cell(m.benchmark.total_return, "pct")],
            ["wynik annualizowany", cell(m.portfolio.annualized_return, "pct"),
             cell(m.benchmark.annualized_return, "pct")],
            ["zmienność roczna", cell(m.portfolio.vol_annualized, "pct"),
             cell(m.benchmark.vol_annualized, "pct")],
            [f"Sharpe (rf={rf:.1%})" if rf else "Sharpe (rf=0%)",
             cell(m.portfolio.sharpe, "sharpe"), cell(m.benchmark.sharpe, "sharpe")],
            ["max drawdown", cell(m.portfolio.max_drawdown, "pct"),
             cell(m.benchmark.max_drawdown, "pct")],
        ]
        metrics_html = (
            f"<p>n={m.n_points} sesji, okres {m.days:.0f} dni "
            f"({series['date'].iloc[0][:10]} &rarr; {series['date'].iloc[-1][:10]}) — "
            f"założenie statycznego składu portfela</p>"
            + _table(["metryka", "portfel", "S&P 500 (PLN)"], rows))

    alloc_rows = []
    for cls, target in snap.targets.items():
        share, drift = snap.allocation[cls], snap.drift_pp[cls]
        bar = (f'<div class="bar"><div class="fill" '
               f'style="width:{min(share * 100, 100):.1f}%"></div></div>')
        alloc_rows.append([escape(cls), f"{share * 100:.1f}%",
                           f"{target * 100:.1f}%", f"{drift:+.1f}", bar])
    alloc_html = _table(["klasa", "udział", "target", "dryf [p.p.]",
                         "udział (wizualnie)"], alloc_rows)

    pos_rows = []
    for _, r in snap.positions.iterrows():
        weight = float(r["value_base"]) / snap.total_value
        pos_rows.append([
            escape(str(r["ticker"])), escape(str(r["asset_class"])),
            f"{r['quantity']:g}", f"{r['price']:,.4f}",
            escape(str(r["currency"])), f"{r['fx_rate']:.4f}",
            f"{r['value_base']:,.2f} {escape(base)}", f"{weight * 100:.1f}%",
        ])
    pos_html = _table(["ticker", "klasa", "ilość", "cena", "waluta", "FX",
                       "wartość", "% portfela"], pos_rows)

    hist_path = Path("reports/history.csv")
    hist_pts = str(len(pd.read_csv(hist_path))) if hist_path.exists() else "0"

    css = (
        "body{font-family:system-ui,'Segoe UI',Arial,sans-serif;margin:0;"
        "background:#f3f4f6;color:#111827}"
        "header{background:#111827;color:#fff;padding:16px 24px}"
        "header p{margin:4px 0 0;font-size:12px;color:#9ca3af}"
        "h1{margin:0;font-size:20px}"
        ".wrap{max-width:1100px;margin:0 auto;padding:20px 24px 8px}"
        ".note{background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;"
        "padding:10px 14px;font-size:13px;margin:12px 24px}"
        "section{background:#fff;border-radius:10px;padding:16px 20px;"
        "margin-bottom:18px;box-shadow:0 1px 3px rgba(0,0,0,.08)}"
        "h2{font-size:13px;margin:0 0 10px;color:#374151;text-transform:uppercase;"
        "letter-spacing:.05em}"
        "table{border-collapse:collapse;width:100%;font-size:14px}"
        "th,td{padding:6px 10px;border-bottom:1px solid #e5e7eb;text-align:left}"
        "th{color:#6b7280;font-weight:600}"
        ".kpis{display:flex;gap:14px;flex-wrap:wrap}"
        ".kpi{flex:1;min-width:180px;background:#fff;border-radius:10px;"
        "padding:12px 16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}"
        ".kpi .v{font-size:20px;font-weight:700}"
        ".kpi .l{font-size:12px;color:#6b7280}"
        ".bar{background:#e5e7eb;border-radius:4px;height:14px;width:160px}"
        ".fill{background:#2563eb;height:14px;border-radius:4px}"
        "footer{color:#6b7280;font-size:12px;padding:4px 24px 24px}"
    )
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>inv-adv — wyniki portfela</title>
<style>{css}</style>
</head>
<body>
<header>
  <h1>inv-adv — wyniki portfela</h1>
  <p>wygenerowano: {escape(generated)} | waluta bazowa: {escape(base)} | \
benchmark: {escape(str(cfg['benchmark']['ticker']))}</p>
</header>
<div class="note"><b>LOKALNY PLIK</b> — zawiera pełne dane pozycyjne i kwoty. \
Nie publikuj w internecie (site/ jest w .gitignore).</div>
<div class="wrap">
  <div class="kpis">
    <div class="kpi"><div class="v">{snap.total_value:,.2f} {escape(base)}</div>
      <div class="l">wartość portfela</div></div>
    <div class="kpi"><div class="v">{snap.benchmark_value:,.2f} {escape(base)}</div>
      <div class="l">S&amp;P 500 — 1 jedn. ({escape(str(cfg['benchmark']['ticker']))})</div></div>
    <div class="kpi"><div class="v">{len(snap.positions)}</div>
      <div class="l">pozycji</div></div>
    <div class="kpi"><div class="v">{hist_pts}</div>
      <div class="l">punktów historii biegów (F1)</div></div>
  </div>
  <section><h2>Metryki (F1 — statyczny skład)</h2>{metrics_html}</section>
  <section><h2>Wydajność — base 100</h2>{chart}</section>
  <section><h2>Alokacja klas vs targety</h2>{alloc_html}</section>
  <section><h2>Pozycje</h2>{pos_html}</section>
</div>
<footer>Źródła: data/portfolio.csv, config.yaml, Yahoo Finance. \
Założenia: statyczny skład w rekonstrukcji historycznej; {escape(base)} jako waluta bazowa. \
Plik lokalny — nie publikować.</footer>
</body>
</html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="inv-adv: lokalny dashboard HTML (pełne dane, nie publikować)")
    parser.add_argument("--period", default="1y", help="okres rekonstrukcji: 6mo/1y/2y/max")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--portfolio", default="data/portfolio.csv")
    parser.add_argument("--out", default=str(SITE_PATH))
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config))
    portfolio = load_portfolio(Path(args.portfolio))
    prices, manual = fetch_prices(collect_tickers(portfolio, cfg))
    close = fetch_history_prices(collect_history_tickers(portfolio, cfg), args.period)
    series = build_series(portfolio, close, cfg)
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = build_page(cfg, portfolio, prices, series, generated)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    note = f" (ceny ręczne: {', '.join(manual)})" if manual else ""
    print(f"Dashboard: {out}{note}")
    print("Plik lokalny z pełnymi danymi — nie publikować w internecie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
