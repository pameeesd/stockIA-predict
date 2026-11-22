#!/usr/bin/env python3
"""Reproducible one-week-ahead forecasting benchmark for StockIA Predict.

Input: UK product-week sales CSV from scripts/01_audit_dataset.py.
No raw workbook is included. Predictions target recorded positive sales,
not latent demand, inventory depletion or lost sales.
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

KNOWN_NON_MERCHANDISE_CODES = {
    "DOT", "M", "C2", "POST", "BANK CHARGES", "GIFT_0001_30"
}
FEATURES = [
    "lag_1", "lag_2", "lag_3", "lag_4", "lag_8", "lag_13",
    "mean_4", "mean_8", "mean_13", "std_4", "nonzero_13",
    "max_13", "mean4_minus_mean13", "mean_26", "mean_52", "lag_52",
    "has_lag_52", "mean_history", "active_rate_history",
    "mean_positive_history", "cv_history", "week_sin", "week_cos"
]


def score(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.maximum(0.0, np.asarray(y_pred, dtype=float))
    denom = float(np.sum(np.abs(y_true)))
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "WAPE_pct": float(100*np.sum(np.abs(y_true-y_pred))/denom) if denom else float("nan"),
        "actual_units": float(y_true.sum()),
        "predicted_units": float(y_pred.sum()),
        "bias_units": float((y_pred-y_true).sum()),
    }


def load_panel(path, train_end=72, min_active=20):
    df = pd.read_csv(path, parse_dates=["WeekStart"], dtype={"StockCode_str": str})
    need = {"StockCode_str", "WeekStart", "UnitsSold"}
    if not need.issubset(df.columns):
        raise ValueError(f"Missing columns: {sorted(need-set(df.columns))}")
    df["SKU"] = df["StockCode_str"].astype(str).str.strip().str.upper()
    normalized_codes = int(df["SKU"].nunique())
    raw_codes = int(df["StockCode_str"].nunique())
    df = df.groupby(["SKU", "WeekStart"], as_index=False).agg(UnitsSold=("UnitsSold", "sum"))
    weeks = pd.date_range(df.WeekStart.min(), df.WeekStart.max(), freq="7D")
    if len(weeks) != 104:
        raise ValueError(f"Expected 104 calendar weeks, got {len(weeks)}")
    absent_weeks = [str(w.date()) for w in weeks if w not in set(df.WeekStart.unique())]
    panel = df.pivot(index="SKU", columns="WeekStart", values="UnitsSold").reindex(columns=weeks).fillna(0.0).sort_index()
    active_train = (panel.iloc[:, :train_end] > 0).sum(axis=1)
    eligible = active_train >= min_active
    excluded_existing = sorted(set(panel.index).intersection(KNOWN_NON_MERCHANDISE_CODES))
    chosen = panel.loc[eligible & ~panel.index.isin(KNOWN_NON_MERCHANDISE_CODES)].copy()
    profile = {
        "aggregated_rows_before_panel": int(len(df)),
        "raw_case_sensitive_codes": raw_codes,
        "case_normalized_codes": normalized_codes,
        "case_variants_merged": raw_codes-normalized_codes,
        "calendar_weeks": int(len(weeks)),
        "weeks_with_no_recorded_UK_sales": absent_weeks,
        "codes_with_minimum_activity": int(eligible.sum()),
        "known_non_merchandise_codes_excluded": excluded_existing,
        "selected_item_codes": int(chosen.shape[0]),
        "selection_rule": f">={min_active} nonzero weeks within first {train_end} training weeks",
        "first_week": str(weeks[0].date()),
        "last_week": str(weeks[-1].date()),
    }
    return chosen.to_numpy(dtype=np.float32), weeks, chosen.index.tolist(), profile


def make_xy(y_matrix, weeks, target_indices):
    x_parts, y_parts = [], []
    for t in target_indices:
        w1, w2, w3, w4 = (y_matrix[:, t-k] for k in (1,2,3,4))
        w8, w13 = y_matrix[:, t-8], y_matrix[:, t-13]
        a4 = y_matrix[:, t-4:t]
        a8 = y_matrix[:, t-8:t]
        a13 = y_matrix[:, t-13:t]
        week_no = int(weeks[t].isocalendar().week)
        hist = y_matrix[:, :t]
        last26 = y_matrix[:, max(0,t-26):t]
        last52 = y_matrix[:, max(0,t-52):t]
        has_lag52 = float(t >= 52)
        lag52 = y_matrix[:, t-52] if t >= 52 else np.zeros(y_matrix.shape[0], dtype=np.float32)
        positive_count = (hist > 0).sum(axis=1)
        positive_sum = np.where(hist > 0, hist, 0.0).sum(axis=1)
        mean_positive = np.divide(positive_sum, positive_count, out=np.zeros_like(positive_sum, dtype=float), where=positive_count > 0)
        x = np.column_stack([
            w1, w2, w3, w4, w8, w13,
            a4.mean(axis=1), a8.mean(axis=1), a13.mean(axis=1),
            a4.std(axis=1), (a13>0).sum(axis=1), a13.max(axis=1),
            a4.mean(axis=1)-a13.mean(axis=1),
            last26.mean(axis=1), last52.mean(axis=1), lag52,
            np.full(y_matrix.shape[0], has_lag52),
            hist.mean(axis=1), (hist>0).mean(axis=1),
            mean_positive,
            hist.std(axis=1)/(hist.mean(axis=1)+1.0),
            np.full(y_matrix.shape[0], np.sin(2*np.pi*week_no/52.0)),
            np.full(y_matrix.shape[0], np.cos(2*np.pi*week_no/52.0)),
        ]).astype(np.float32)
        x_parts.append(x)
        y_parts.append(y_matrix[:,t].astype(np.float32))
    return np.vstack(x_parts), np.concatenate(y_parts)


def baseline(y_matrix, target_indices, name):
    parts=[]
    for t in target_indices:
        if name == "last_week": p=y_matrix[:,t-1]
        elif name == "mean_4": p=y_matrix[:,t-4:t].mean(axis=1)
        elif name == "mean_13": p=y_matrix[:,t-13:t].mean(axis=1)
        elif name == "seasonal_52": p=y_matrix[:,t-52] if t>=52 else y_matrix[:,t-1]
        else: raise ValueError(name)
        parts.append(p)
    return np.concatenate(parts)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",type=Path,default=Path("reports/generated/uk_product_week_sales.csv"))
    ap.add_argument("--output",type=Path,default=Path("reports/ml_experiment"))
    ap.add_argument("--skip-xgboost",action="store_true")
    args=ap.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    started=time.time()
    panel,weeks,skus,profile=load_panel(args.input)
    train_idx=list(range(13,72)); val_idx=list(range(72,88)); test_idx=list(range(88,104))
    Xtr,ytr=make_xy(panel,weeks,train_idx)
    Xv,yv=make_xy(panel,weeks,val_idx)
    Xtest,ytest=make_xy(panel,weeks,test_idx)
    profile.update({
        "split": {
            "train_target_weeks":[str(weeks[train_idx[0]].date()),str(weeks[train_idx[-1]].date())],
            "validation_target_weeks":[str(weeks[val_idx[0]].date()),str(weeks[val_idx[-1]].date())],
            "test_target_weeks":[str(weeks[test_idx[0]].date()),str(weeks[test_idx[-1]].date())]},
        "train_examples":int(len(ytr)),"validation_examples":int(len(yv)),"test_examples":int(len(ytest)),
        "features":FEATURES,"target":"weekly positive recorded sales quantity, UK, by item code",
        "target_transform":"log1p for machine-learning regressors",
    })
    rows=[]
    test_prediction_map = {"actual_units": ytest}
    for name in ["last_week","mean_4","mean_13","seasonal_52"]:
        rows.append({"model":name,"split":"validation",**score(yv,baseline(panel,val_idx,name))})
        p_test = baseline(panel,test_idx,name)
        rows.append({"model":name,"split":"test",**score(ytest,p_test)})
        if name == "mean_13":
            test_prediction_map["mean_13_baseline"] = p_test

    # Validation-phase global gradient boosting model.
    hgb=HistGradientBoostingRegressor(
        max_iter=180,learning_rate=0.07,max_leaf_nodes=31,
        min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,
        random_state=42
    )
    t0=time.time(); hgb.fit(Xtr,np.log1p(ytr)); hgb_train_sec=time.time()-t0
    hgb_val=np.expm1(hgb.predict(Xv)).clip(min=0)
    rows.append({"model":"hist_gradient_boosting","split":"validation",**score(yv,hgb_val)})
    Xtrv=np.vstack([Xtr,Xv]); ytrv=np.concatenate([ytr,yv])
    hgb_final=HistGradientBoostingRegressor(
        max_iter=180,learning_rate=0.07,max_leaf_nodes=31,
        min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,
        random_state=42
    )
    hgb_final.fit(Xtrv,np.log1p(ytrv))
    hgb_test=np.expm1(hgb_final.predict(Xtest)).clip(min=0)
    rows.append({"model":"hist_gradient_boosting","split":"test",**score(ytest,hgb_test)})
    test_prediction_map["hist_gradient_boosting"] = hgb_test
    profile["hist_gradient_boosting_train_seconds"] = round(hgb_train_sec,2)

    # Poisson objective on the original non-negative quantity scale.
    poisson=HistGradientBoostingRegressor(
        loss="poisson",max_iter=180,learning_rate=0.06,max_leaf_nodes=31,
        min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,
        random_state=42
    )
    t0=time.time(); poisson.fit(Xtr,ytr); poisson_train_sec=time.time()-t0
    poisson_val=np.maximum(poisson.predict(Xv),0.0)
    rows.append({"model":"hgb_poisson","split":"validation",**score(yv,poisson_val)})
    poisson_final=HistGradientBoostingRegressor(
        loss="poisson",max_iter=180,learning_rate=0.06,max_leaf_nodes=31,
        min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,
        random_state=42
    )
    poisson_final.fit(Xtrv,ytrv)
    poisson_test=np.maximum(poisson_final.predict(Xtest),0.0)
    rows.append({"model":"hgb_poisson","split":"test",**score(ytest,poisson_test)})
    test_prediction_map["hgb_poisson"] = poisson_test
    profile["hist_gradient_boosting_poisson_train_seconds"] = round(poisson_train_sec,2)

    # Two-stage (hurdle) model: probability of a positive sale, then expected
    # positive quantity conditional on a sale. Conditional size is fitted on log1p.
    hurdle_clf=HistGradientBoostingClassifier(
        max_iter=140,learning_rate=0.06,max_leaf_nodes=31,
        min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,
        random_state=42
    )
    hurdle_reg=HistGradientBoostingRegressor(
        max_iter=180,learning_rate=0.06,max_leaf_nodes=31,
        min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,
        random_state=42
    )
    t0=time.time()
    hurdle_clf.fit(Xtr,(ytr>0).astype(int))
    positive_train=(ytr>0)
    hurdle_reg.fit(Xtr[positive_train],np.log1p(ytr[positive_train]))
    hurdle_train_sec=time.time()-t0
    hurdle_val=(hurdle_clf.predict_proba(Xv)[:,1] * np.expm1(hurdle_reg.predict(Xv)).clip(min=0))
    rows.append({"model":"hgb_hurdle","split":"validation",**score(yv,hurdle_val)})
    hurdle_clf_final=HistGradientBoostingClassifier(
        max_iter=140,learning_rate=0.06,max_leaf_nodes=31,
        min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,
        random_state=42
    )
    hurdle_reg_final=HistGradientBoostingRegressor(
        max_iter=180,learning_rate=0.06,max_leaf_nodes=31,
        min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,
        random_state=42
    )
    hurdle_clf_final.fit(Xtrv,(ytrv>0).astype(int))
    positive_train_val=(ytrv>0)
    hurdle_reg_final.fit(Xtrv[positive_train_val],np.log1p(ytrv[positive_train_val]))
    hurdle_test=(hurdle_clf_final.predict_proba(Xtest)[:,1] * np.expm1(hurdle_reg_final.predict(Xtest)).clip(min=0))
    rows.append({"model":"hgb_hurdle","split":"test",**score(ytest,hurdle_test)})
    test_prediction_map["hgb_hurdle"] = hurdle_test
    profile["hist_gradient_boosting_hurdle_train_seconds"] = round(hurdle_train_sec,2)
    profile["positive_week_share"] = {
        "train":float(np.mean(ytr>0)),"validation":float(np.mean(yv>0)),"test":float(np.mean(ytest>0))
    }

    if not args.skip_xgboost:
        try:
            from xgboost import XGBRegressor
            xgb=XGBRegressor(
                n_estimators=350,max_depth=5,learning_rate=0.05,
                subsample=0.85,colsample_bytree=0.9,min_child_weight=10,
                reg_lambda=2.0,objective="reg:squarederror",eval_metric="rmse",
                tree_method="hist",n_jobs=6,random_state=42,
                early_stopping_rounds=30
            )
            t0=time.time(); xgb.fit(Xtr,np.log1p(ytr),eval_set=[(Xv,np.log1p(yv))],verbose=False)
            xgb_train_sec=time.time()-t0
            xgb_val=np.expm1(xgb.predict(Xv)).clip(min=0)
            rows.append({"model":"xgboost","split":"validation",**score(yv,xgb_val)})
            best_n=int(getattr(xgb,"best_iteration",349) or 349)+1
            xgb_final=XGBRegressor(
                n_estimators=best_n,max_depth=5,learning_rate=0.05,
                subsample=0.85,colsample_bytree=0.9,min_child_weight=10,
                reg_lambda=2.0,objective="reg:squarederror",eval_metric="rmse",
                tree_method="hist",n_jobs=6,random_state=42
            )
            xgb_final.fit(Xtrv,np.log1p(ytrv),verbose=False)
            xgb_test=np.expm1(xgb_final.predict(Xtest)).clip(min=0)
            rows.append({"model":"xgboost","split":"test",**score(ytest,xgb_test)})
            test_prediction_map["xgboost"] = xgb_test
            importance = pd.DataFrame({"feature":FEATURES,"importance":xgb_final.feature_importances_}).sort_values("importance",ascending=False)
            importance.to_csv(args.output/"xgboost_feature_importance.csv",index=False)
            profile["xgboost_best_trees"] = best_n
            profile["xgboost_train_seconds"] = round(xgb_train_sec,2)
        except ImportError:
            profile["xgboost_status"]="not installed; skipped"

    result=pd.DataFrame(rows)
    result.to_csv(args.output/"model_metrics.csv",index=False)

    n_sku = len(skus)
    pred_detail = pd.DataFrame({
        "SKU": np.tile(np.asarray(skus, dtype=str), len(test_idx)),
        "WeekStart": np.repeat([str(weeks[t].date()) for t in test_idx], n_sku),
        **test_prediction_map,
    })
    pred_detail.to_csv(args.output/"test_predictions.csv",index=False)
    weekly_totals = pred_detail.groupby("WeekStart",as_index=False).sum(numeric_only=True)
    weekly_totals.to_csv(args.output/"test_weekly_totals.csv",index=False)

    # Compact, reproducible figures for the academic report and GitHub evidence.
    fig, ax = plt.subplots(figsize=(9,5))
    test_metrics = result[result["split"]=="test"].sort_values("WAPE_pct")
    ax.bar(test_metrics["model"],test_metrics["WAPE_pct"])
    ax.set_title("WAPE en el período de prueba (menor es mejor)")
    ax.set_ylabel("WAPE (%)")
    ax.tick_params(axis="x",rotation=25)
    ax.grid(axis="y",alpha=.25)
    fig.tight_layout(); fig.savefig(args.output/"wape_test_comparison.png",dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10,5))
    x = np.arange(len(weekly_totals))
    ax.plot(x,weekly_totals["actual_units"],marker="o",label="Ventas observadas")
    for c in ["mean_13_baseline","hist_gradient_boosting","hgb_hurdle","hgb_poisson","xgboost"]:
        if c in weekly_totals.columns:
            ax.plot(x,weekly_totals[c],marker=".",label=c)
    ax.set_title("Unidades semanales agregadas: observado vs pronosticado")
    ax.set_xlabel("Semana del conjunto de prueba")
    ax.set_ylabel("Unidades")
    ax.legend(); ax.grid(alpha=.25); fig.tight_layout()
    fig.savefig(args.output/"weekly_totals_test.png",dpi=160); plt.close(fig)

    profile["elapsed_seconds"] = round(time.time()-started,2)
    profile["methodological_notes"] = [
        "The source workbook is not included in this project output; results are derived from its UK weekly aggregate.",
        "Two complete calendar weeks with no UK transaction records are represented as zero weeks: 2009-12-28 and 2010-12-27.",
        "StockCode is uppercased before re-aggregation; case-only variants are merged.",
        "SKU eligibility uses only training-window activity, so future validation/test data do not affect selection.",
        "Known non-merchandise codes are excluded; catalogue review remains necessary for final release.",
        "All ML features are calculated using weeks strictly before the forecast target week.",
        "Evaluation is rolling one-step-ahead: actual previous weeks are assumed available before each next-week forecast.",
        "Zeros mean no recorded positive sales, not confirmed stock availability.",
        "Target is recorded sales quantity. The source does not include inventory on hand, stockouts, lost sales, procurement costs or supplier lead times.",
        "The final 16 weeks are not used to fit model parameters; this exploratory benchmark compares several pre-specified candidates on that period, so later model selection must use rolling-origin backtesting rather than repeatedly optimizing against this same holdout."
    ]
    (args.output/"experiment_profile.json").write_text(json.dumps(profile,indent=2),encoding="utf-8")
    print(result.to_string(index=False))
    print("\nProfile:",json.dumps(profile,indent=2))

if __name__=="__main__":
    main()
