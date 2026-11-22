#!/usr/bin/env python3
"""Diagnose unusually large invoices for the most underforecast products.

The script reads the original UCI workbook locally, restricts the analysis to
positive UK sales in the exploratory test window, and exports only aggregated
invoice statistics. Invoice numbers and CustomerIDs are never written out.
"""
from __future__ import annotations
import argparse, csv, re, time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import pandas as pd

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
START = datetime(2011, 8, 15)
END = datetime(2011, 12, 5)  # exclusive

def clean_sku(value):
    if isinstance(value, (int, float)) and float(value).is_integer():
        return str(int(value)).upper()
    s = str(value).strip().upper()
    return re.sub(r'\.0$', '', s)

def parse_sheet2(workbook: Path, target_skus: set[str]):
    invoice_sku = defaultdict(lambda: {'qty': 0, 'description': '', 'date': '', 'customers': set()})
    sku_customers = defaultdict(set)
    seen = set()
    parsed_rows = deduplicated = retained_lines = 0
    with ZipFile(workbook) as zf:
        shared = []
        for _, elem in etree.iterparse(zf.open('xl/sharedStrings.xml'), events=('end',), tag=NS+'si'):
            shared.append(''.join(elem.itertext()))
            elem.clear()
        for _, row in etree.iterparse(zf.open('xl/worksheets/sheet2.xml'), events=('end',), tag=NS+'row', huge_tree=True):
            if row.get('r') != '1':
                vals = [None] * 8
                for cell in row.findall(NS+'c'):
                    col = ''.join(ch for ch in cell.get('r', '') if ch.isalpha())
                    if len(col) != 1:
                        continue
                    idx = ord(col) - 65
                    if idx > 7:
                        continue
                    typ = cell.get('t')
                    v = cell.find(NS+'v')
                    if typ == 'inlineStr':
                        isel = cell.find(NS+'is')
                        value = ''.join(isel.itertext()) if isel is not None else None
                    elif v is None:
                        value = None
                    elif typ == 's':
                        value = shared[int(v.text)]
                    elif typ == 'str':
                        value = v.text
                    else:
                        try: value = float(v.text)
                        except (TypeError, ValueError): value = v.text
                    vals[idx] = value
                parsed_rows += 1
                tup = tuple(vals)
                if tup in seen:
                    deduplicated += 1
                else:
                    seen.add(tup)
                    invoice, stock, desc, qty, excel_date, price, customer, country = vals
                    if (country == 'United Kingdom' and not str(invoice).strip().upper().startswith('C')
                        and isinstance(qty, (int, float)) and qty > 0 and isinstance(excel_date, float)):
                        dt = datetime(1899, 12, 30) + timedelta(days=excel_date)
                        if START <= dt < END:
                            sku = clean_sku(stock)
                            if sku in target_skus:
                                key = (sku, str(invoice).strip())
                                record = invoice_sku[key]
                                record['qty'] += int(qty)
                                record['description'] = str(desc or '')
                                record['date'] = dt.date().isoformat()
                                if customer is not None:
                                    record['customers'].add(customer)
                                    sku_customers[sku].add(customer)
                                retained_lines += 1
            row.clear()
            while row.getprevious() is not None:
                del row.getparent()[0]
    return invoice_sku, sku_customers, {'sheet_rows_parsed': parsed_rows, 'exact_duplicate_rows_skipped': deduplicated, 'retained_target_transaction_lines': retained_lines}

def main():
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workbook', type=Path, default=root/'data/raw/online_retail_II.xlsx')
    ap.add_argument('--underforecast-csv', type=Path, default=root/'reports/segment_diagnostics/product_underprediction_test.csv')
    ap.add_argument('--output', type=Path, default=root/'reports/segment_diagnostics')
    ap.add_argument('--top-n', type=int, default=25)
    args = ap.parse_args()
    if not args.workbook.exists():
        raise FileNotFoundError(f'Workbook not found: {args.workbook}. Download it from UCI and place it in data/raw/.')
    products = pd.read_csv(args.underforecast_csv, dtype={'SKU': str})
    products['SKU'] = products['SKU'].map(clean_sku)
    target = set(products.sort_values('under_units', ascending=False).head(args.top_n)['SKU'])
    started = time.time()
    invoice_sku, sku_customers, parse_profile = parse_sheet2(args.workbook, target)
    by_sku = defaultdict(list)
    largest_by_sku = {}
    for (sku, _invoice), rec in invoice_sku.items():
        by_sku[sku].append(rec['qty'])
        if sku not in largest_by_sku or rec['qty'] > largest_by_sku[sku]['qty']:
            largest_by_sku[sku] = rec
    stats, examples = [], []
    for sku, quantities in by_sku.items():
        q = pd.Series(quantities, dtype='float64')
        total = float(q.sum())
        largest = largest_by_sku[sku]
        stats.append({
            'SKU': sku, 'Invoices': int(q.size), 'DistinctCustomerIDs': len(sku_customers[sku]),
            'TotalUnits': int(total), 'MedianUnitsPerInvoice': float(q.median()),
            'P90UnitsPerInvoice': float(q.quantile(.90)), 'P95UnitsPerInvoice': float(q.quantile(.95)),
            'P99UnitsPerInvoice': float(q.quantile(.99)), 'MaxUnitsPerInvoice': int(q.max()),
            'LargestInvoiceSharePct': float(q.max()/total*100 if total else 0)
        })
        examples.append({'SKU': sku, 'Description': largest['description'], 'Date': largest['date'],
                         'UnitsInLargestInvoice': int(largest['qty']),
                         'ShareSKUUnitsInTestPct': float(largest['qty']/total*100 if total else 0)})
    args.output.mkdir(parents=True, exist_ok=True)
    stats_df = pd.DataFrame(stats).merge(products[['SKU','DemandPattern','actual_units','predicted_units','under_units']], on='SKU', how='left')
    stats_df.sort_values('under_units', ascending=False).to_csv(args.output/'invoice_order_stats_sanitized.csv', index=False)
    pd.DataFrame(examples).sort_values('ShareSKUUnitsInTestPct', ascending=False).to_csv(args.output/'largest_invoice_examples_sanitized.csv', index=False)
    (args.output/'invoice_diagnostics_profile.json').write_text(
        __import__('json').dumps({**parse_profile, 'target_skus': len(target), 'invoices_with_target_skus': len(invoice_sku),
                                 'test_window_start_inclusive': START.date().isoformat(),
                                 'test_window_end_exclusive': END.date().isoformat(),
                                 'privacy': 'InvoiceNo and CustomerID are not exported.'}, indent=2), encoding='utf-8')
    print(f'Completed in {time.time()-started:.1f}s; invoice/SKU pairs={len(invoice_sku)}; target SKUs={len(target)}')

if __name__ == '__main__':
    main()
