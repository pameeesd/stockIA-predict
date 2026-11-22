#!/usr/bin/env python3
"""Reproduce the initial audit of the UCI Online Retail II workbook.

The raw workbook is not bundled in this repository. Download it from UCI and
place it at data/raw/online_retail_II.xlsx, then run:
    python scripts/01_audit_dataset.py

Outputs are descriptive and do not train a forecasting model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

EXPECTED = [
    "InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
    "UnitPrice", "CustomerID", "Country"
]


def load_workbook(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    frames = []
    for sheet_name, frame in sheets.items():
        frame = frame.rename(columns={
            "Invoice": "InvoiceNo",
            "Price": "UnitPrice",
            "Customer ID": "CustomerID",
        })
        missing = [c for c in EXPECTED if c not in frame.columns]
        if missing:
            raise ValueError(f"Missing columns in sheet {sheet_name}: {missing}")
        frame = frame[EXPECTED].copy()
        frame["_source_sheet"] = sheet_name
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce")
    data["InvoiceNo_str"] = data["InvoiceNo"].astype(str).str.strip()
    data["StockCode_str"] = data["StockCode"].astype(str).str.strip().str.upper()
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/online_retail_II.xlsx"))
    parser.add_argument("--output", type=Path, default=Path("reports/generated"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    figure_dir = args.output / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    if not args.input.exists():
        raise FileNotFoundError(
            f"Workbook not found: {args.input}. Download the official UCI file; "
            "do not commit the raw workbook to a public repository."
        )

    raw = load_workbook(args.input)
    raw_rows = len(raw)
    duplicate_count = int(raw.duplicated(subset=EXPECTED).sum())
    clean = raw.drop_duplicates(subset=EXPECTED, keep="first").copy()

    is_cancel = clean["InvoiceNo_str"].str.upper().str.startswith("C")
    positive_non_cancel = clean[(~is_cancel) & (clean["Quantity"] > 0)].copy()
    # This is an initial transaction-level filter, not yet the final product
    # catalogue. Special service/fee/adjustment codes still require review.

    uk = positive_non_cancel[positive_non_cancel["Country"].eq("United Kingdom")].copy()
    uk["WeekStart"] = uk["InvoiceDate"].dt.to_period("W-SUN").apply(lambda p: p.start_time)
    uk["Month"] = uk["InvoiceDate"].dt.to_period("M").astype(str)

    # Exclude edge partial weeks, but preserve all calendar weeks in the
    # observation window for the downstream model to zero-fill explicitly.
    observed_weeks = sorted(uk["WeekStart"].dropna().unique())
    # Exclude the first and last partial calendar weeks using the data's observed
    # date span, then reconstruct every full calendar week (including weeks with
    # zero UK transactions). A transaction-derived list alone omits such weeks.
    first_full_week = uk["WeekStart"].min() + pd.Timedelta(days=7)
    last_full_week = uk["WeekStart"].max() - pd.Timedelta(days=7)
    full_week_starts = pd.date_range(first_full_week, last_full_week, freq="7D")
    uk_full = uk[uk["WeekStart"].isin(full_week_starts)].copy()
    uk_weeks_with_sales = sorted(uk_full["WeekStart"].dropna().unique())
    zero_sales_weeks = [str(w.date()) for w in full_week_starts if w not in set(uk_weeks_with_sales)]

    weekly = (uk_full.groupby(["StockCode_str", "WeekStart"], as_index=False)
              .agg(UnitsSold=("Quantity", "sum"),
                   SalesLines=("InvoiceNo", "size"),
                   InvoiceCount=("InvoiceNo", "nunique")))
    coverage = (weekly.groupby("StockCode_str")
                .agg(ActiveWeeks=("WeekStart", "nunique"),
                     TotalUnits=("UnitsSold", "sum"),
                     SalesLines=("SalesLines", "sum"))
                .sort_values(["ActiveWeeks", "TotalUnits"], ascending=False))

    monthly = (uk.groupby("Month", as_index=False)
               .agg(SalesLines=("InvoiceNo", "size"),
                    UnitsSold=("Quantity", "sum"),
                    InvoiceCount=("InvoiceNo", "nunique")))
    top_products = coverage.head(50).reset_index()
    active_product_codes = int(weekly["StockCode_str"].nunique())

    def pct(n: int, d: int) -> float:
        return round((n / d * 100) if d else 0, 4)

    customer_null = int(clean["CustomerID"].isna().sum())
    description_null = int(clean["Description"].isna().sum())
    c_invoice_rows = int(clean["InvoiceNo_str"].str.upper().str.startswith("C").sum())
    negative_quantity = int((clean["Quantity"] < 0).sum())
    zero_price = int((clean["UnitPrice"] == 0).sum())
    negative_price = int((clean["UnitPrice"] < 0).sum())
    date_min = clean["InvoiceDate"].min()
    date_max = clean["InvoiceDate"].max()
    profile = {
        "source": "UCI Machine Learning Repository - Online Retail II",
        "raw_file": args.input.name,
        "raw_rows": raw_rows,
        "exact_duplicate_rows_removed": duplicate_count,
        "exact_duplicate_percent": pct(duplicate_count, raw_rows),
        "rows_after_exact_deduplication": len(clean),
        "date_min": date_min.isoformat() if pd.notna(date_min) else None,
        "date_max": date_max.isoformat() if pd.notna(date_max) else None,
        "unique_calendar_dates": int(clean["InvoiceDate"].dt.date.nunique()),
        "unique_invoices": int(clean["InvoiceNo_str"].nunique()),
        "unique_stock_codes": int(clean["StockCode_str"].nunique()),
        "unique_customer_ids_non_null": int(clean["CustomerID"].nunique()),
        "unique_countries": int(clean["Country"].nunique()),
        "missing_customer_id": customer_null,
        "missing_customer_id_percent": pct(customer_null, len(clean)),
        "missing_description": description_null,
        "missing_description_percent": pct(description_null, len(clean)),
        "cancellation_invoice_rows": c_invoice_rows,
        "cancellation_invoice_rows_percent": pct(c_invoice_rows, len(clean)),
        "negative_quantity_rows": negative_quantity,
        "negative_quantity_rows_percent": pct(negative_quantity, len(clean)),
        "zero_unit_price_rows": zero_price,
        "negative_unit_price_rows": negative_price,
        "positive_non_cancellation_rows_after_dedup": len(positive_non_cancel),
        "positive_non_cancellation_units_after_dedup": int(positive_non_cancel["Quantity"].sum()),
        "uk_positive_non_cancellation_rows": len(uk),
        "uk_share_of_positive_rows_percent": pct(len(uk), len(positive_non_cancel)),
        "uk_positive_non_cancellation_units": int(uk["Quantity"].sum()),
        "uk_share_of_units_percent": pct(int(uk["Quantity"].sum()), int(positive_non_cancel["Quantity"].sum())),
        "uk_unique_stock_codes_normalized": int(uk["StockCode_str"].nunique()),
        "uk_week_buckets_with_transactions_including_partial_edges": len(observed_weeks),
        "uk_full_calendar_weeks_for_modelling": len(full_week_starts),
        "uk_full_calendar_weeks_with_any_sales": len(uk_weeks_with_sales),
        "uk_full_calendar_weeks_with_zero_sales": zero_sales_weeks,
        "uk_observed_product_week_combinations": len(weekly),
        "uk_active_product_codes_in_full_weeks": active_product_codes,
        "uk_full_panel_cells": int(active_product_codes * len(full_week_starts)),
        "uk_product_week_occupancy_percent": pct(len(weekly), int(active_product_codes * len(full_week_starts))),
        "uk_full_week_units": int(uk_full["Quantity"].sum()),
        "uk_products_with_at_least_20_active_weeks": int((coverage["ActiveWeeks"] >= 20).sum()),
        "uk_products_with_at_least_50_active_weeks": int((coverage["ActiveWeeks"] >= 50).sum()),
        "uk_products_with_at_least_80_active_weeks": int((coverage["ActiveWeeks"] >= 80).sum()),
        "notes": [
            "The source describes an anonymized UK-based non-store online retailer.",
            "Sales rows are not the same as latent demand: stockouts and lost sales are not observed.",
            "Exact duplicates are removed in the analytical copy; raw workbook remains unchanged.",
            "Cancelled invoices and non-positive quantities are not used as sales demand; they remain available for separate analysis.",
            "Service, fee, voucher and adjustment StockCodes require a documented product-catalogue exclusion review before final model training.",
            "The first and last weekly buckets are partial observation windows and are excluded; all 104 complete calendar weeks between them are retained, including two with no UK transactions.",
            "StockCode is converted to uppercase before weekly aggregation to merge case-only variants.",
            "No on-hand inventory, purchase orders, supplier lead times, procurement costs or lost-sales fields are present."
        ]
    }

    (args.output / "dataset_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    monthly.to_csv(args.output / "uk_monthly_sales_summary.csv", index=False)
    weekly.to_csv(args.output / "uk_product_week_sales.csv", index=False)
    top_products.to_csv(args.output / "top_50_sku_coverage.csv", index=False)

    # Charts use matplotlib defaults to keep them portable and reproducible.
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(pd.to_datetime(monthly["Month"]), monthly["SalesLines"], marker="o")
    ax.set_title("UK sales transaction lines by month")
    ax.set_xlabel("Month")
    ax.set_ylabel("Positive non-cancelled sales lines")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / "uk_monthly_sales_lines.png", dpi=160)
    plt.close(fig)

    missing = pd.Series({
        "CustomerID": pct(customer_null, len(clean)),
        "Description": pct(description_null, len(clean)),
        "Other columns": 0.0,
    })
    fig, ax = plt.subplots(figsize=(8, 4.2))
    missing.sort_values(ascending=False).plot(kind="bar", ax=ax)
    ax.set_title("Missing values by field")
    ax.set_ylabel("Rows with missing value (%)")
    ax.set_xlabel("Field")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / "missing_values.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    coverage["ActiveWeeks"].plot(kind="hist", bins=25, ax=ax)
    ax.set_title("Distribution of active weeks per SKU (UK, full weeks)")
    ax.set_xlabel("Number of weeks with recorded sales")
    ax.set_ylabel("Number of SKUs")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / "sku_active_weeks_distribution.png", dpi=160)
    plt.close(fig)

    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
