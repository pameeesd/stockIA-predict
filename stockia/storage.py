"""Persistencia en SQLite: ejecuciones, pronósticos guardados y decisiones del usuario.

Nunca se guardan identificadores de clientes ni números de factura.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DEFAULT_DB = Path(os.environ.get("STOCKIA_DB", Path(__file__).resolve().parents[1] / "data" / "app" / "stockia.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  source TEXT NOT NULL,
  data_cutoff TEXT NOT NULL,
  n_items INTEGER NOT NULL,
  alpha REAL NOT NULL,
  weeks INTEGER NOT NULL,
  params TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS forecasts (
  run_id INTEGER NOT NULL REFERENCES runs(id),
  sku TEXT NOT NULL,
  description TEXT,
  segment TEXT,
  reliability TEXT,
  tsb REAL NOT NULL,
  reference REAL NOT NULL,
  review_status TEXT NOT NULL DEFAULT 'Pendiente',
  adjusted REAL,
  note TEXT,
  PRIMARY KEY (run_id, sku)
);
CREATE TABLE IF NOT EXISTS alert_decisions (
  sku TEXT NOT NULL,
  date TEXT NOT NULL,
  units REAL NOT NULL,
  decision TEXT NOT NULL,
  note TEXT,
  decided_at TEXT NOT NULL,
  PRIMARY KEY (sku, date, units)
);
"""
REVIEW_STATES = ("Pendiente", "Aceptado", "Ajustado")
ALERT_DECISIONS = ("Pendiente", "Conservado", "Excluido")


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path or DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Streamlit ejecuta cada recarga en un hilo distinto; las recargas de una sesión son secuenciales.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_run(conn, source: str, data_cutoff: str, meta: dict, forecasts: pd.DataFrame, params: dict | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO runs (created_at, source, data_cutoff, n_items, alpha, weeks, params) VALUES (?,?,?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), source, data_cutoff, int(meta["items"]), float(meta["alpha"]),
         int(meta["weeks"]), json.dumps(params or {}, ensure_ascii=False, default=str)))
    run_id = int(cur.lastrowid)
    rows = [(run_id, r.sku, r.descripcion, r.segmento, r.fiabilidad, float(r.pronostico_tsb), float(r.referencia_media4))
            for r in forecasts.itertuples()]
    conn.executemany("INSERT INTO forecasts (run_id, sku, description, segment, reliability, tsb, reference) "
                     "VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    return run_id


def list_runs(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM runs ORDER BY id DESC", conn)


def load_forecasts(conn, run_id: int) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM forecasts WHERE run_id = ? ORDER BY tsb DESC", conn, params=(int(run_id),))


def update_review(conn, run_id: int, sku: str, status: str, adjusted: float | None = None, note: str = "") -> None:
    if status not in REVIEW_STATES:
        raise ValueError(f"Estado no válido: {status}")
    conn.execute("UPDATE forecasts SET review_status=?, adjusted=?, note=? WHERE run_id=? AND sku=?",
                 (status, adjusted, note, int(run_id), sku))
    conn.commit()


def save_alert_decision(conn, sku: str, date: str, units: float, decision: str, note: str = "") -> None:
    if decision not in ALERT_DECISIONS:
        raise ValueError(f"Decisión no válida: {decision}")
    conn.execute("INSERT OR REPLACE INTO alert_decisions (sku, date, units, decision, note, decided_at) VALUES (?,?,?,?,?,?)",
                 (str(sku), str(date), float(units), decision, note, datetime.now().isoformat(timespec="seconds")))
    conn.commit()


def load_alert_decisions(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM alert_decisions", conn)


def exclusions(conn) -> pd.DataFrame:
    """Líneas que el usuario excluyó del historial (columnas sku, date, units)."""
    df = load_alert_decisions(conn)
    return df[df["decision"] == "Excluido"][["sku", "date", "units"]].reset_index(drop=True)
