# Reproducibility check

The model-training script included in this repository was rerun against the same UK product-week aggregation used for the reported benchmark. Its `model_metrics.csv` matched the published benchmark table exactly (maximum absolute difference across MAE, RMSE, WAPE, actual units, predicted units and bias: 0.0).

The end-to-end raw workbook audit was not included as a continuous integration test because parsing the 43.5 MB Excel workbook is resource-intensive in this environment. Run `01_audit_dataset.py` locally with the official UCI workbook to regenerate the weekly aggregation before running the model script.
