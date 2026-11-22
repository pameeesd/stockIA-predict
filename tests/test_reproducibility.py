"""Reproduce el resultado oficial (docs/RESULTADOS.md) ejecutando el script de backtesting sin ML."""
import subprocess
import sys

import pandas as pd
import pytest


@pytest.mark.slow
def test_statistical_results_match_published_numbers(root, tmp_path):
    out = tmp_path / "backtesting"
    subprocess.run(
        [sys.executable, str(root / "scripts" / "05_backtesting_model_selection.py"), "--skip-ml", "--output", str(out)],
        check=True, capture_output=True, text=True, cwd=root,
    )
    m = pd.read_csv(out / "model_metrics.csv").set_index("strategy")
    # Cifras de docs/RESULTADOS.md (no dependen de los modelos ML)
    assert m.loc["tsb_selected", "WAPE_pct"] == pytest.approx(77.00, abs=0.005)
    assert m.loc["tsb_selected", "bias_pct"] == pytest.approx(-6.13, abs=0.005)
    assert m.loc["mean_4", "WAPE_pct"] == pytest.approx(78.65, abs=0.005)
    assert m.loc["mean_13", "WAPE_pct"] == pytest.approx(83.56, abs=0.005)
    assert m.loc["tsb_selected", "WAPE_pct"] < m.loc["mean_4", "WAPE_pct"]  # TSB mejora a la línea base

    folds = pd.read_csv(out / "fold_metrics.csv")
    tsb = folds[folds.strategy == "tsb_selected"].set_index("fold")["WAPE_pct"]
    base = folds[folds.strategy == "mean_4"].set_index("fold")["WAPE_pct"]
    assert int((tsb < base).sum()) == 4  # TSB supera a la línea base en 4 de 6 bloques

    chosen = pd.read_csv(out / "selected_candidates.csv")
    chosen = chosen[chosen.strategy == "tsb_selected"].set_index("fold")["selected"]
    assert list(chosen) == ["tsb_0.50", "tsb_0.50", "tsb_0.30", "tsb_0.20", "tsb_0.30", "tsb_0.20"]
