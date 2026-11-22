#!/usr/bin/env python3
"""Genera los datos de demostración de la app a partir del Excel original de UCI.

    python scripts/06_build_demo_assets.py --input data/raw/online_retail_II.xlsx

Salidas en data/demo/ (sin números de factura ni identificadores de clientes):
  product_descriptions.csv   código y descripción más frecuente de cada artículo (Reino Unido)
  volume_alerts_uci.csv      facturas de volumen inusual por artículo (regla de stockia.alerts)
  quality_report_uci.json    resumen de calidad del archivo original
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stockia import alerts, ingest  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=ROOT / "data/raw/online_retail_II.xlsx")
    ap.add_argument("--output", type=Path, default=ROOT / "data/demo")
    ap.add_argument("--country", default="United Kingdom")
    args = ap.parse_args()
    if not args.input.exists():
        raise SystemExit(f"No existe {args.input}. Descargue Online Retail II de UCI (CC BY 4.0) en data/raw/.")
    args.output.mkdir(parents=True, exist_ok=True)

    raw = ingest.read_table(args.input, args.input.name)
    report = ingest.quality_report(raw)
    report = {k: (str(v) if k.startswith("date_") else v) for k, v in report.items()}
    (args.output / "quality_report_uci.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ingest.clean_lines(raw, country=args.country)
    desc = (lines.dropna(subset=["Description"]).groupby("StockCode_str")["Description"]
            .agg(lambda s: s.mode().iat[0]).str.strip().rename("Description").reset_index()
            .rename(columns={"StockCode_str": "SKU"}))
    desc.to_csv(args.output / "product_descriptions.csv", index=False, encoding="utf-8")

    found = alerts.detect_volume_alerts(lines)
    found.to_csv(args.output / "volume_alerts_uci.csv", index=False, encoding="utf-8")
    print(f"Líneas de venta {args.country}: {len(lines):,} · descripciones: {len(desc):,} · alertas: {len(found):,}")
    print(found.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
