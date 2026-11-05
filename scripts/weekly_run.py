#!/usr/bin/env python3
"""Cotygodniowy bieg inv-adv na maszynie z harmonogramem (Windows/Linux).

Robi dokładnie to samo co `scripts/weekly_run.ps1`, ale bez PowerShella:
1. `python run.py --scheduled` — jeden idempotentny punkt paper tradingu,
2. `python -m inv_adv.publish` — lokalny dashboard,
3. log do `reports/logs/run-YYYY-MM-DD.log`,
4. opcjonalny alert na `INV_ADV_ALERT_WEBHOOK` (JSON POST) przy błędzie.

Uruchamiaj z katalogu repo lub przez harmonogram z pełną ścieżką do
interpretera z venv. Nie wymaga sieci poza normalnym cyklem run.py.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "reports" / "logs"
STATUS_PATH = ROOT / "reports" / "status.json"


def _log(path: Path, message: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _run_step(cmd: list[str], log_path: Path) -> int:
    _log(log_path, "RUN " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                          env={**os.environ, "PYTHONUNBUFFERED": "1"})
    if proc.stdout:
        _log(log_path, "stdout:\n" + proc.stdout.rstrip())
    if proc.stderr:
        _log(log_path, "stderr:\n" + proc.stderr.rstrip())
    _log(log_path, f"exit={proc.returncode}")
    return proc.returncode


def _write_error(step: str, message: str) -> None:
    sys.path.insert(0, str(ROOT))
    from inv_adv.status import write_status  # działa również poza katalogiem repo

    write_status(path=STATUS_PATH, status="error", run_kind="scheduled",
                 step=step, error=message)


def _notify(payload: dict) -> None:
    url = os.getenv("INV_ADV_ALERT_WEBHOOK", "").strip()
    if not url:
        return
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            _ = resp.read()
    except Exception as exc:  # alert nie może wywalić biegu
        print(f"alert webhook failed: {type(exc).__name__}: {exc}", file=sys.stderr)


def main() -> int:
    log_path = LOG_DIR / f"run-{dt.date.today():%Y-%m-%d}.log"
    _log(log_path, "=== inv-adv weekly run ===")

    code = _run_step([sys.executable, "run.py", "--scheduled"], log_path)
    if code != 0:
        msg = f"run.py zakończony kodem {code}; punkt historii nie został poprawnie zapisany"
        _log(log_path, "BLAD: " + msg)
        _write_error("run.py", msg)
        _notify({"status": "error", "step": "run.py", "message": msg})
        return code

    code = _run_step([sys.executable, "-m", "inv_adv.publish"], log_path)
    if code != 0:
        msg = f"publish zakończony kodem {code}; protokół OK, dashboard nieodświeżony"
        _log(log_path, "BLAD: " + msg)
        _write_error("publish", msg)
        _notify({"status": "error", "step": "publish", "message": msg})
        return code

    _log(log_path, "ZAKONCZONO OK")
    _notify({"status": "ok", "step": "weekly_run", "message": "bieg zakończony"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
