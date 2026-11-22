from pathlib import Path
import argparse, importlib.util, json, time, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Segmentación ADI/CV² y benchmark por patrón de demanda para StockIA.')
parser.add_argument('--input', type=Path, default=ROOT/'data/processed/uk_product_week_sales.csv', help='Panel semanal derivado de Online Retail II.')
parser.add_argument('--output', type=Path, default=ROOT/'reports/segment_diagnostics', help='Carpeta de salida.')
parser.add_argument('--write-predictions', action='store_true', help='Guardar todas las predicciones (puede crear CSV grande).')
args = parser.parse_args()
BASE = ROOT/'scripts/02_train_forecasting_models.py'
INPUT = args.input.resolve()
OUT = args.output.resolve()
WRITE_PREDICTIONS = args.write_predictions
OUT.mkdir(parents=True, exist_ok=True)
t0=time.time()
spec=importlib.util.spec_from_file_location('stockia_bench',BASE); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
panel,weeks,skus,profile=mod.load_panel(INPUT,train_end=72,min_active=20)
n_sku=len(skus)
train_idx=list(range(13,72)); val_idx=list(range(72,88)); test_idx=list(range(88,104))
Xtr,ytr=mod.make_xy(panel,weeks,train_idx); Xv,yv=mod.make_xy(panel,weeks,val_idx); Xt,yt=mod.make_xy(panel,weeks,test_idx)

# Segmentation uses only the first 72 calendar weeks, never validation/test outcomes.
seg_rows=[]; train_hist=panel[:,:72]
for i,sku in enumerate(skus):
    h=train_hist[i].astype(float)
    pos=h[h>0]; npos=len(pos); adi=72.0/npos if npos else np.inf
    mean_pos=float(pos.mean()) if npos else 0.0
    cv2=float(np.var(pos,ddof=1)/(mean_pos**2)) if npos>1 and mean_pos>0 else 0.0
    if adi<1.32 and cv2<0.49: cls='smooth'
    elif adi<1.32 and cv2>=0.49: cls='erratic'
    elif adi>=1.32 and cv2<0.49: cls='intermittent'
    else: cls='lumpy'
    med=float(np.median(pos)) if npos else 0.0
    p95=float(np.quantile(pos,.95)) if npos else 0.0
    maxv=float(pos.max()) if npos else 0.0
    total=float(h.sum())
    max_share=maxv/total if total>0 else 0.0
    burst_ratio=maxv/med if med>0 else np.nan
    seg_rows.append({'SKU':sku,'DemandPattern':cls,'ADI':adi,'CV2_positive_weekly':cv2,'ActiveWeeksTrain':npos,
                     'ActiveRateTrain':npos/72,'MeanPositiveWeeklyUnits':mean_pos,'MeanWeeklyUnits':float(h.mean()),
                     'MedianPositiveWeeklyUnits':med,'P95PositiveWeeklyUnits':p95,'MaxPositiveWeeklyUnits':maxv,
                     'MaxWeekShareTrain':max_share,'MaxToMedianPositiveRatio':burst_ratio,'TrainUnits':total})
seg=pd.DataFrame(seg_rows)
# Concentrated-volume flag: relative top decile of max-week share; descriptive, not a wholesale label.
spike_threshold=float(seg['MaxWeekShareTrain'].quantile(.90))
seg['EpisodicConcentration']='high' if False else 'normal'
seg.loc[seg['MaxWeekShareTrain']>=spike_threshold,'EpisodicConcentration']='high'
seg.to_csv(OUT/'sku_training_segments.csv',index=False)

# Fit model candidates using training only; validate to compare; refit train+validation for final test diagnostics.
models={}; predictions={}; metric_rows=[]
# Baselines
for name in ['last_week','mean_4','mean_13','seasonal_52']:
    predictions[(name,'validation')]=mod.baseline(panel,val_idx,name)
    predictions[(name,'test')]=mod.baseline(panel,test_idx,name)

hgb_params=dict(max_iter=180,learning_rate=0.07,max_leaf_nodes=31,min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,random_state=42)
hgb=HistGradientBoostingRegressor(**hgb_params); hgb.fit(Xtr,np.log1p(ytr)); predictions[('hgb_log1p','validation')]=np.expm1(hgb.predict(Xv)).clip(min=0)
Xtrv=np.vstack([Xtr,Xv]); ytrv=np.concatenate([ytr,yv])
hgb2=HistGradientBoostingRegressor(**hgb_params); hgb2.fit(Xtrv,np.log1p(ytrv)); predictions[('hgb_log1p','test')]=np.expm1(hgb2.predict(Xt)).clip(min=0)

poi_params=dict(loss='poisson',max_iter=180,learning_rate=0.06,max_leaf_nodes=31,min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,random_state=42)
poi=HistGradientBoostingRegressor(**poi_params); poi.fit(Xtr,ytr); predictions[('hgb_poisson','validation')]=np.maximum(poi.predict(Xv),0)
poi2=HistGradientBoostingRegressor(**poi_params); poi2.fit(Xtrv,ytrv); predictions[('hgb_poisson','test')]=np.maximum(poi2.predict(Xt),0)

clf_params=dict(max_iter=140,learning_rate=0.06,max_leaf_nodes=31,min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,random_state=42)
reg_params=dict(max_iter=180,learning_rate=0.06,max_leaf_nodes=31,min_samples_leaf=35,l2_regularization=1.0,early_stopping=False,random_state=42)
cl=HistGradientBoostingClassifier(**clf_params); cl.fit(Xtr,(ytr>0).astype(int))
rp=HistGradientBoostingRegressor(**reg_params); mpos=ytr>0; rp.fit(Xtr[mpos],np.log1p(ytr[mpos]))
predictions[('hgb_hurdle','validation')]=cl.predict_proba(Xv)[:,1]*np.expm1(rp.predict(Xv)).clip(min=0)
cl2=HistGradientBoostingClassifier(**clf_params); cl2.fit(Xtrv,(ytrv>0).astype(int))
rp2=HistGradientBoostingRegressor(**reg_params); mpos2=ytrv>0; rp2.fit(Xtrv[mpos2],np.log1p(ytrv[mpos2]))
predictions[('hgb_hurdle','test')]=cl2.predict_proba(Xt)[:,1]*np.expm1(rp2.predict(Xt)).clip(min=0)

# XGBoost optional, same features and temporal validation.
try:
    from xgboost import XGBRegressor
    xgb=XGBRegressor(n_estimators=350,max_depth=5,learning_rate=0.05,subsample=.85,colsample_bytree=.9,min_child_weight=10,reg_lambda=2.0,objective='reg:squarederror',eval_metric='rmse',tree_method='hist',n_jobs=4,random_state=42,early_stopping_rounds=30)
    xgb.fit(Xtr,np.log1p(ytr),eval_set=[(Xv,np.log1p(yv))],verbose=False)
    predictions[('xgboost_log1p','validation')]=np.expm1(xgb.predict(Xv)).clip(min=0)
    best_n=int(getattr(xgb,'best_iteration',349) or 349)+1
    xgb2=XGBRegressor(n_estimators=best_n,max_depth=5,learning_rate=.05,subsample=.85,colsample_bytree=.9,min_child_weight=10,reg_lambda=2.0,objective='reg:squarederror',eval_metric='rmse',tree_method='hist',n_jobs=4,random_state=42)
    xgb2.fit(Xtrv,np.log1p(ytrv),verbose=False)
    predictions[('xgboost_log1p','test')]=np.expm1(xgb2.predict(Xt)).clip(min=0)
except Exception as e:
    print('XGBoost skipped:',repr(e))

# Store prediction rows with SKU/time and training-only segment labels.
segment_lookup=seg.set_index('SKU')['DemandPattern'].to_dict()
conc_lookup=seg.set_index('SKU')['EpisodicConcentration'].to_dict()
val_weeks=[str(weeks[t].date()) for t in val_idx]; test_weeks=[str(weeks[t].date()) for t in test_idx]
pred_dfs=[]
for (model,split),p in predictions.items():
    idx=val_idx if split=='validation' else test_idx
    y=yv if split=='validation' else yt
    p=np.maximum(0,np.asarray(p,dtype=float))
    frame=pd.DataFrame({'SKU':np.tile(np.asarray(skus,dtype=str),len(idx)),
                        'WeekStart':np.repeat([str(weeks[t].date()) for t in idx],n_sku),
                        'actual_units':y,'predicted_units':p,'model':model,'split':split})
    frame['DemandPattern']=frame.SKU.map(segment_lookup)
    frame['EpisodicConcentration']=frame.SKU.map(conc_lookup)
    pred_dfs.append(frame)
all_preds=pd.concat(pred_dfs,ignore_index=True)
if WRITE_PREDICTIONS:
    all_preds.to_csv(OUT/'predictions_by_sku_week.csv',index=False)

# Overall metrics and per-segment metrics.
def metrics(y,p):
    y=np.asarray(y,float);p=np.maximum(0,np.asarray(p,float));den=y.sum()
    return {'n_sku_week':len(y),'actual_units':y.sum(),'predicted_units':p.sum(),'bias_units':p.sum()-y.sum(),
            'bias_pct':(p.sum()-y.sum())/den*100 if den else np.nan,
            'MAE':mean_absolute_error(y,p),'RMSE':np.sqrt(mean_squared_error(y,p)),
            'WAPE_pct':np.abs(y-p).sum()/den*100 if den else np.nan}
for (model,split),p in predictions.items():
    idx=val_idx if split=='validation' else test_idx; y=yv if split=='validation' else yt
    metric_rows.append({'model':model,'split':split,'segment':'ALL',**metrics(y,p)})
    frame=all_preds[(all_preds.model==model)&(all_preds.split==split)]
    for cls,g in frame.groupby('DemandPattern'):
        metric_rows.append({'model':model,'split':split,'segment':cls,**metrics(g.actual_units,g.predicted_units),
                            'n_products':g.SKU.nunique(),'share_actual_units_pct':g.actual_units.sum()/y.sum()*100 if y.sum() else np.nan})
    for cls,g in frame.groupby('EpisodicConcentration'):
        metric_rows.append({'model':model,'split':split,'segment':'concentration_'+cls,**metrics(g.actual_units,g.predicted_units),
                            'n_products':g.SKU.nunique(),'share_actual_units_pct':g.actual_units.sum()/y.sum()*100 if y.sum() else np.nan})
met=pd.DataFrame(metric_rows);met.to_csv(OUT/'segment_metrics.csv',index=False)

# Product-level diagnostics for the globally selected validation model, and separately test diagnostics.
val_all=met[(met.split=='validation')&(met.segment=='ALL')].sort_values('WAPE_pct')
best_model=str(val_all.iloc[0].model)
print('Selected on validation WAPE:',best_model)
for split in ['validation','test']:
    g=all_preds[(all_preds.model==best_model)&(all_preds.split==split)].groupby('SKU',as_index=False).agg(
        actual_units=('actual_units','sum'),predicted_units=('predicted_units','sum'),absolute_error=('predicted_units',lambda x:0.0))
    # compute true absolute error separately without awkward lambda
    tmp=all_preds[(all_preds.model==best_model)&(all_preds.split==split)].copy();tmp['abs_error']=(tmp.actual_units-tmp.predicted_units).abs();tmp['under_units']=(tmp.actual_units-tmp.predicted_units).clip(lower=0);tmp['over_units']=(tmp.predicted_units-tmp.actual_units).clip(lower=0)
    d=tmp.groupby('SKU',as_index=False).agg(actual_units=('actual_units','sum'),predicted_units=('predicted_units','sum'),abs_error=('abs_error','sum'),under_units=('under_units','sum'),over_units=('over_units','sum'),n_weeks=('WeekStart','nunique'))
    d=d.merge(seg,on='SKU',how='left'); d['bias_units']=d.predicted_units-d.actual_units;d['bias_pct']=np.where(d.actual_units>0,d.bias_units/d.actual_units*100,np.nan)
    d.sort_values('under_units',ascending=False).to_csv(OUT/f'product_underprediction_{split}.csv',index=False)

# Summaries for concise report.
segment_counts=seg.groupby('DemandPattern').agg(Products=('SKU','nunique'),MedianActiveRate=('ActiveRateTrain','median'),MedianCV2=('CV2_positive_weekly','median'),MedianADI=('ADI','median'),TrainingUnits=('TrainUnits','sum')).reset_index()
segment_counts.to_csv(OUT/'segment_profile_summary.csv',index=False)
profile_out={'selected_products':n_sku,'segment_thresholds':{'ADI':1.32,'CV2':0.49},'episodic_concentration_threshold_max_week_share_q90':spike_threshold,
             'selection_rule':'>=20 positive weeks in first 72 calendar weeks; normalized StockCode; excluded known service/fee/adjustment codes',
             'split':{'training_targets':len(train_idx),'validation_targets':len(val_idx),'test_targets':len(test_idx)},
             'best_global_model_selected_on_validation_WAPE':best_model,
             'validation_overall_metrics':val_all.iloc[0].to_dict(),
             'notes':['All product segments use first 72 calendar weeks only.','ADI/CV2 uses the standard four-pattern demand classification; threshold ADI=1.32, CV2=0.49.','High concentration is a descriptive top-decile flag on maximum weekly share, not proof of wholesale orders.','Sales target is recorded positive units, not latent demand or lost sales.','Test-set segment metrics are diagnostic only; use validation or future rolling-origin backtests for model selection.']}
(OUT/'segment_experiment_profile.json').write_text(json.dumps(profile_out,indent=2,default=str))

# Chart: validation WAPE by pattern for baseline and ML models.
plot=met[(met.split=='validation')&(met.segment.isin(['smooth','erratic','intermittent','lumpy']))].copy()
if not plot.empty:
    piv=plot.pivot(index='segment',columns='model',values='WAPE_pct')
    fig,ax=plt.subplots(figsize=(10,5));piv.plot(kind='bar',ax=ax)
    ax.set_title('WAPE en validación por patrón de demanda (menor es mejor)');ax.set_ylabel('WAPE (%)');ax.set_xlabel('Patrón (clasificado solo con entrenamiento)');ax.grid(axis='y',alpha=.25);ax.legend(fontsize=8,ncol=2);fig.tight_layout();fig.savefig(OUT/'validation_wape_by_demand_pattern.png',dpi=160);plt.close(fig)

print('\nSegment counts:\n',segment_counts.to_string(index=False))
print('\nValidation metrics by segment:\n',met[(met.split=='validation')].sort_values(['segment','WAPE_pct']).to_string(index=False))
print('\nTest overall metrics:\n',met[(met.split=='test')&(met.segment=='ALL')].sort_values('WAPE_pct').to_string(index=False))
print('\nProfile:',json.dumps(profile_out,indent=2,default=str))
print('Elapsed seconds:',round(time.time()-t0,1))
