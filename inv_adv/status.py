"""Operacyjny manifest ostatniego biegu (bez danych pozycyjnych).

`reports/status.json` jest lekkim, maszynowo czytelnym stanem dla monitoringu:
kiedy poszedł bieg, jaki był wynik, ile jest punktów historii i czy metryki
są już gotowe. Nie zapisujemy tu wartości portfela ani pozycji.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

STATUS_PATH = Path("reports/status.json")


def write_status(path: Path = STATUS_PATH, **fields: Any) -> dict[str, Any]:
    """Atomowo zapisuje status biegu (najpierw plik tymczasowy, potem replace)."""
    payload: dict[str, Any] = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        **fields,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    tmp.replace(path)
    return payload


def read_status(path: Path = STATUS_PATH) -> dict[str, Any]:
    """Czyta status; brak pliku zwraca pusty słownik."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
