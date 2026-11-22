"""Backtesting multi-origen y selección final de modelo para StockIA (Documento 06).

Reconstruye el experimento descrito en el Documento 06:

* Cohorte fija: artículos con >=20 semanas de venta positiva en las primeras 56
  semanas (sin códigos de cargos/servicios conocidos).
* Seis orígenes externos (índices 56, 64, 72, 80, 88, 96). Cada uno evalúa un
  bloque disjunto de 8 semanas; los candidatos se comparan en las 8 semanas
  inmediatamente anteriores (validación interna) y solo esa ventana decide.
* Pronóstico de un paso adelante en modo rolling: la venta real de cada semana
  se incorpora al historial antes de pronosticar la siguiente.
* Candidatos: última semana, medias móviles 4/13, Croston, SBA y TSB (alfa en
  {0,05..0,50}; en TSB alfa = beta), HGB Poisson, HGB Hurdle Poisson, LightGBM
  Poisson con código de artículo categórico, híbrido por segmento ADI/CV² y
  híbrido calibrado por segmento.

Uso:
    python scripts/05_backtesting_model_selection.py
    python scripts/05_backtesting_model_selection.py --skip-ml          # solo métodos estadísticos (rápido)
    python scripts/05_backtesting_model_selection.py --write-predictions
"""
from pathlib import Path
import argparse
import importlib.util
import json
import time
import warnings

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
ORIGINS = [56, 64, 72, 80, 88, 96]
BLOCK = 8
ALPHAS = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50]
ADI_CUT, CV2_CUT = 1.32, 0.49
SEGMENTS = ["smooth", "erratic", "intermittent", "lumpy"]
FIRST_FEATURE_WEEK = 13  # make_xy necesita 13 semanas de contexto

LABELS = {
    "tsb_selected": "TSB seleccionado por validación interna",
    "hybrid_segment": "Híbrido por segmentos",
    "mean_4": "Promedio móvil de 4 semanas",
    "best_intermittent_selected": "Mejor método intermitente seleccionado internamente",
    "best_statistical_selected": "Mejor método estadístico seleccionado internamente",
    "hybrid_segment_calibrated": "Híbrido calibrado por segmento",
    "hgb_hurdle_poisson": "HGB Hurdle Poisson (ML)",
    "hgb_poisson": "HGB Poisson (ML)",
    "lightgbm_poisson_sku": "LightGBM Poisson con SKU categórico (ML)",
    "mean_13": "Promedio móvil de 13 semanas",
    "last_week": "Última semana",
    "croston_selected": "Croston seleccionado por validación interna",
    "sba_selected": "SBA seleccionado por validación interna",
}


def load_bench_module():
    spec = importlib.util.spec_from_file_location("stockia_bench", ROOT / "scripts/02_train_forecasting_models.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def wape(actual, pred):
    denom = float(np.abs(actual).sum())
    return float(100 * np.abs(actual - pred).sum() / denom) if denom else float("nan")


def score(actual, pred):
    actual = np.asarray(actual, dtype=float)
    pred = np.maximum(0.0, np.asarray(pred, dtype=float))
    err = pred - actual
    return {
        "WAPE_pct": wape(actual, pred),
        "MAE": float(np.abs(err).mean()),
        "RMSE": float(np.sqrt((err ** 2).mean())),
        "bias_pct": float(100 * err.sum() / actual.sum()) if actual.sum() else float("nan"),
        "actual_units": float(actual.sum()),
        "predicted_units": float(pred.sum()),
    }


# ---------------------------------------------------------------------------
# Métodos estadísticos. Cada función devuelve F de forma (n, T+1) donde F[:, t]
# es el pronóstico de la semana t usando solo semanas < t.
# ---------------------------------------------------------------------------

def forecast_last_week(Y):
    return np.concatenate([np.zeros((Y.shape[0], 1)), Y], axis=1)


def forecast_moving_average(Y, k):
    n, T = Y.shape
    F = np.zeros((n, T + 1))
    for t in range(1, T + 1):
        F[:, t] = Y[:, max(0, t - k):t].mean(axis=1)
    return F


def forecast_tsb(Y, alpha, beta):
    """Teunter-Syntetos-Babai. Se inicializa en la primera venta positiva (p=1, z=y)."""
    n, T = Y.shape
    F = np.zeros((n, T + 1))
    p = np.zeros(n)
    z = np.zeros(n)
    started = np.zeros(n, dtype=bool)
    for t in range(T):
        F[:, t] = np.where(started, p * z, 0.0)
        y = Y[:, t]
        positive = y > 0
        newly = ~started & positive
        p = np.where(newly, 1.0, p)
        z = np.where(newly, y, z)
        p = np.where(started, p + beta * (positive.astype(float) - p), p)
        z = np.where(started & positive, z + alpha * (y - z), z)
        started |= newly
    F[:, T] = np.where(started, p * z, 0.0)
    return F


def forecast_croston(Y, alpha, sba=False):
    """Croston (y SBA con factor 1 - alfa/2). Intervalo inicial = semanas hasta la primera venta."""
    n, T = Y.shape
    F = np.zeros((n, T + 1))
    factor = (1 - alpha / 2) if sba else 1.0
    z = np.zeros(n)
    p = np.ones(n)
    q = np.zeros(n)
    started = np.zeros(n, dtype=bool)
    for t in range(T):
        F[:, t] = np.where(started, z / p, 0.0) * factor
        y = Y[:, t]
        q = q + 1
        positive = y > 0
        newly = ~started & positive
        update = started & positive
        z = np.where(newly, y, np.where(update, z + alpha * (y - z), z))
        p = np.where(newly, q, np.where(update, p + alpha * (q - p), p))
        q = np.where(positive, 0, q)
        started |= newly
    F[:, T] = np.where(started, z / p, 0.0) * factor
    return F


def statistical_candidates(Y):
    C = {
        "last_week": forecast_last_week(Y),
        "mean_4": forecast_moving_average(Y, 4),
        "mean_13": forecast_moving_average(Y, 13),
    }
    for a in ALPHAS:
        C[f"croston_{a:.2f}"] = forecast_croston(Y, a)
        C[f"sba_{a:.2f}"] = forecast_croston(Y, a, sba=True)
        C[f"tsb_{a:.2f}"] = forecast_tsb(Y, a, a)
    return C


# ---------------------------------------------------------------------------
# Machine Learning: se reentrena en cada origen. Para puntuar la ventana interna
# se entrena con objetivos < inicio de la ventana interna; para el bloque externo
# se entrena con objetivos < origen. Hiperparámetros fijos.
# ---------------------------------------------------------------------------

def ml_candidates(Y, weeks, mod, origins):
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

    try:
        import lightgbm as lgb
    except ImportError:  # pragma: no cover
        lgb = None
        warnings.warn("lightgbm no está instalado; se omite LightGBM.")

    n = Y.shape[0]
    T = Y.shape[1]
    names = ["hgb_poisson", "hgb_hurdle_poisson"] + (["lightgbm_poisson_sku"] if lgb else [])
    F = {name: np.full((n, T + 1), np.nan) for name in names}
    sku_codes = np.arange(n)

    common = dict(max_leaf_nodes=31, min_samples_leaf=35, l2_regularization=1.0, early_stopping=False, random_state=42)

    def design(idx):
        X, y = mod.make_xy(Y, weeks, idx)
        sku = np.tile(sku_codes, len(idx))
        return X, y, sku

    def fit_predict(train_idx, pred_idx):
        Xtr, ytr, str_ = design(train_idx)
        Xp, _, sp = design(pred_idx)
        out = {}
        poi = HistGradientBoostingRegressor(loss="poisson", max_iter=180, learning_rate=0.06, **common)
        poi.fit(Xtr, ytr)
        out["hgb_poisson"] = np.maximum(poi.predict(Xp), 0)

        clf = HistGradientBoostingClassifier(max_iter=140, learning_rate=0.06, **common)
        clf.fit(Xtr, (ytr > 0).astype(int))
        pos = ytr > 0
        reg = HistGradientBoostingRegressor(loss="poisson", max_iter=180, learning_rate=0.06, **common)
        reg.fit(Xtr[pos], ytr[pos])
        out["hgb_hurdle_poisson"] = clf.predict_proba(Xp)[:, 1] * np.maximum(reg.predict(Xp), 0)

        if lgb:
            Xtr_l = np.column_stack([Xtr, str_])
            Xp_l = np.column_stack([Xp, sp])
            cat = Xtr_l.shape[1] - 1
            model = lgb.LGBMRegressor(objective="poisson", n_estimators=300, learning_rate=0.05, num_leaves=31,
                                      min_child_samples=35, reg_lambda=1.0, random_state=42, verbose=-1)
            model.fit(Xtr_l, ytr, categorical_feature=[cat])
            out["lightgbm_poisson_sku"] = np.maximum(model.predict(Xp_l), 0)
        return {k: v.reshape(len(pred_idx), n).T for k, v in out.items()}

    for o in origins:
        for start, stop in ((o - BLOCK, o), (o, o + BLOCK)):
            t0 = time.time()
            preds = fit_predict(list(range(FIRST_FEATURE_WEEK, start)), list(range(start, stop)))
            for k, v in preds.items():
                F[k][:, start:stop] = v
            print(f"  ML origen {o} ventana {start}-{stop - 1}: {time.time() - t0:.1f}s", flush=True)
    return F


# ---------------------------------------------------------------------------
# Segmentación ADI/CV² con historial disponible hasta el origen.
# ---------------------------------------------------------------------------

def segment_at(Y, origin):
    hist = Y[:, :origin]
    labels = []
    for h in hist:
        pos = h[h > 0]
        npos = len(pos)
        adi = origin / npos if npos else np.inf
        mean_pos = pos.mean() if npos else 0.0
        cv2 = float(np.var(pos, ddof=1) / mean_pos ** 2) if npos > 1 and mean_pos > 0 else 0.0
        if adi < ADI_CUT:
            labels.append("smooth" if cv2 < CV2_CUT else "erratic")
        else:
            labels.append("intermittent" if cv2 < CV2_CUT else "lumpy")
    return np.array(labels)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=ROOT / "data/processed/uk_product_week_sales.csv")
    ap.add_argument("--output", type=Path, default=ROOT / "reports/backtesting")
    ap.add_argument("--skip-ml", action="store_true", help="Omitir HGB/LightGBM (los híbridos usan solo candidatos estadísticos).")
    ap.add_argument("--write-predictions", action="store_true", help="Guardar predicciones externas por SKU y semana.")
    args = ap.parse_args()
    out = args.output.resolve()
    (out / "figures").mkdir(parents=True, exist_ok=True)
    started = time.time()

    mod = load_bench_module()
    Y, weeks, skus, profile = mod.load_panel(args.input, train_end=ORIGINS[0], min_active=20)
    Y = Y.astype(float)
    n, T = Y.shape
    assert T == 104, T
    print(f"Cohorte: {n} artículos, {T} semanas", flush=True)

    C = statistical_candidates(Y)
    stat_names = list(C)
    if not args.skip_ml:
        print("Entrenando modelos ML por origen...", flush=True)
        C.update(ml_candidates(Y, weeks, mod, ORIGINS))
    ml_names = [k for k in C if k not in stat_names]
    families = {
        "tsb": [k for k in stat_names if k.startswith("tsb_")],
        "croston": [k for k in stat_names if k.startswith("croston_")],
        "sba": [k for k in stat_names if k.startswith("sba_")],
    }
    intermittent_names = families["tsb"] + families["croston"] + families["sba"]

    outer_idx = np.concatenate([np.arange(o, o + BLOCK) for o in ORIGINS])
    A = Y[:, outer_idx]
    strategies = {}  # nombre -> matriz (n, 48)
    selections = []
    seg_outer = np.empty((n, len(outer_idx)), dtype=object)

    def select(pool, origin, rows=slice(None)):
        inner = slice(origin - BLOCK, origin)
        return min(pool, key=lambda k: wape(Y[rows, inner], C[k][rows, inner]))

    for name in ["last_week", "mean_4", "mean_13"] + ml_names:
        strategies[name] = C[name][:, outer_idx]

    selected_specs = {
        "tsb_selected": families["tsb"],
        "croston_selected": families["croston"],
        "sba_selected": families["sba"],
        "best_intermittent_selected": intermittent_names,
        "best_statistical_selected": stat_names,
    }
    for name in selected_specs:
        strategies[name] = np.zeros_like(A)
    strategies["hybrid_segment"] = np.zeros_like(A)
    strategies["hybrid_segment_calibrated"] = np.zeros_like(A)
    hybrid_pool = stat_names + ml_names

    for f, o in enumerate(ORIGINS):
        cols = slice(f * BLOCK, (f + 1) * BLOCK)
        outer = slice(o, o + BLOCK)
        inner = slice(o - BLOCK, o)
        for name, pool in selected_specs.items():
            choice = select(pool, o)
            strategies[name][:, cols] = C[choice][:, outer]
            selections.append({"fold": f + 1, "origin_week": str(weeks[o].date()), "strategy": name,
                               "segment": "all", "selected": choice,
                               "inner_WAPE_pct": wape(Y[:, inner], C[choice][:, inner])})
        seg = segment_at(Y, o)
        seg_outer[:, cols] = seg[:, None]
        for s in SEGMENTS:
            rows = seg == s
            if not rows.any():
                continue
            choice = select(hybrid_pool, o, rows)
            pred_inner = C[choice][rows, inner]
            factor = Y[rows, inner].sum() / pred_inner.sum() if pred_inner.sum() > 0 else 1.0
            strategies["hybrid_segment"][rows, cols] = C[choice][rows, outer]
            strategies["hybrid_segment_calibrated"][rows, cols] = C[choice][rows, outer] * factor
            selections.append({"fold": f + 1, "origin_week": str(weeks[o].date()), "strategy": "hybrid_segment",
                               "segment": s, "selected": choice, "n_products": int(rows.sum()),
                               "inner_WAPE_pct": wape(Y[rows, inner], pred_inner), "calibration_factor": float(factor)})

    order = [k for k in LABELS if k in strategies]
    # Métricas globales
    global_rows = [{"strategy": k, "label": LABELS[k], **score(A, strategies[k])} for k in order]
    gdf = pd.DataFrame(global_rows).sort_values("WAPE_pct")
    gdf.to_csv(out / "model_metrics.csv", index=False)

    # Métricas por fold
    fold_rows = []
    for f, o in enumerate(ORIGINS):
        cols = slice(f * BLOCK, (f + 1) * BLOCK)
        for k in order:
            fold_rows.append({"fold": f + 1, "start": str(weeks[o].date()), "end": str(weeks[o + BLOCK - 1].date()),
                              "strategy": k, **score(A[:, cols], strategies[k][:, cols])})
    fdf = pd.DataFrame(fold_rows)
    fdf.to_csv(out / "fold_metrics.csv", index=False)

    # Métricas por segmento (segmento recalculado en cada origen)
    seg_rows = []
    for s in SEGMENTS:
        mask = seg_outer == s
        for k in order:
            seg_rows.append({"segment": s, "strategy": k, "n_sku_week": int(mask.sum()),
                             **score(A[mask], strategies[k][mask])})
    sdf = pd.DataFrame(seg_rows)
    sdf.to_csv(out / "segment_metrics.csv", index=False)

    # Métricas por producto (solo artículos con ventas en el período externo)
    active = A.sum(axis=1) > 0
    base_abs = np.abs(A - strategies["mean_4"]).sum(axis=1)
    sku_rows = []
    for k in order:
        abs_err = np.abs(A - strategies[k]).sum(axis=1)
        sku_wape = 100 * abs_err[active] / A[active].sum(axis=1)
        sku_rows.append({"strategy": k, "products_with_sales": int(active.sum()),
                         "median_sku_WAPE_pct": float(np.median(sku_wape)),
                         "mean_sku_WAPE_pct": float(np.mean(sku_wape)),
                         "p75_sku_WAPE_pct": float(np.percentile(sku_wape, 75)),
                         "p90_sku_WAPE_pct": float(np.percentile(sku_wape, 90)),
                         "pct_products_better_than_mean4": float(100 * (abs_err[active] < base_abs[active]).mean())})
    kdf = pd.DataFrame(sku_rows)
    kdf.to_csv(out / "sku_level_metrics.csv", index=False)
    pd.DataFrame(selections).to_csv(out / "selected_candidates.csv", index=False)

    if args.write_predictions:
        rows = {"SKU": np.repeat(skus, len(outer_idx)), "WeekStart": np.tile(weeks[outer_idx].date, n),
                "segment": seg_outer.ravel(), "actual_units": A.ravel()}
        rows.update({k: strategies[k].ravel() for k in order})
        pd.DataFrame(rows).to_csv(out / "outer_predictions.csv", index=False)

    profile.update({
        "cohort_rule": ">=20 positive weeks in first 56 calendar weeks, known non-merchandise codes excluded",
        "cohort_products": int(n),
        "products_with_sales_in_outer_blocks": int(active.sum()),
        "outer_observations": int(A.size),
        "outer_actual_units": float(A.sum()),
        "origins": {f + 1: str(weeks[o].date()) for f, o in enumerate(ORIGINS)},
        "block_weeks": BLOCK,
        "alpha_grid": ALPHAS,
        "segmentation": {"ADI_cut": ADI_CUT, "CV2_cut": CV2_CUT, "history": "weeks before each origin"},
        "ml_included": not args.skip_ml,
        "runtime_seconds": round(time.time() - started, 1),
    })
    (out / "experiment_profile.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")

    make_figures(out / "figures", gdf, fdf, sdf, kdf)
    pd.set_option("display.width", 160)
    print(gdf[["label", "WAPE_pct", "MAE", "RMSE", "bias_pct"]].round(2).to_string(index=False))
    print(f"\nListo en {time.time() - started:.0f}s. Resultados en {out}")


def make_figures(fig_dir, gdf, fdf, sdf, kdf):
    main_keys = [k for k in ["mean_4", "tsb_selected", "hybrid_segment"] if k in set(gdf.strategy)]

    d = gdf.sort_values("WAPE_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#2f6f4f" if k == "tsb_selected" else "#8a8f98" for k in d.strategy]
    ax.barh(d.label, d.WAPE_pct, color=colors)
    for y, v in enumerate(d.WAPE_pct):
        ax.text(v + 0.5, y, f"{v:.2f}%", va="center", fontsize=8)
    ax.set_xlabel("WAPE fuera de muestra (%)")
    ax.set_title("Comparación de estrategias (6 bloques externos)")
    fig.tight_layout(); fig.savefig(fig_dir / "global_wape_comparison.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k in main_keys:
        s = fdf[fdf.strategy == k]
        ax.plot(s.fold, s.WAPE_pct, marker="o", label=LABELS[k])
    ax.set_xlabel("Fold externo"); ax.set_ylabel("WAPE (%)"); ax.set_title("WAPE por bloque externo")
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(fig_dir / "wape_by_fold.png", dpi=150); plt.close(fig)

    piv = sdf[sdf.strategy.isin(main_keys)].pivot(index="segment", columns="strategy", values="WAPE_pct").reindex(SEGMENTS)[main_keys]
    ax = piv.rename(columns=LABELS).plot.bar(figsize=(8, 4.5), rot=0)
    ax.set_ylabel("WAPE (%)"); ax.set_title("WAPE por patrón de demanda")
    ax.legend(fontsize=8); plt.tight_layout(); plt.savefig(fig_dir / "wape_by_segment.png", dpi=150); plt.close()

    k = kdf[kdf.strategy.isin(main_keys)].set_index("strategy").reindex(main_keys)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    names = [LABELS[x] for x in k.index]
    axes[0].bar(names, k.median_sku_WAPE_pct, color="#4c72b0"); axes[0].set_title("Mediana WAPE por SKU (%)")
    axes[1].bar(names, k.pct_products_better_than_mean4, color="#55a868"); axes[1].set_title("% productos mejor que mean4")
    for a in axes:
        a.tick_params(axis="x", labelrotation=15, labelsize=7)
    fig.tight_layout(); fig.savefig(fig_dir / "sku_level_comparison.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    main()
