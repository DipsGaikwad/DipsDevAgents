"""Loads the locally bundled progression model when present.
If unavailable, emits a transparent trend-based screening result without inventing a probability.
"""
from pathlib import Path
import pandas as pd
MODEL_FILE=Path(__file__).resolve().parents[2]/'models'/'trained'/'ckd_model.joblib'
FEATURES=['age_at_baseline','gender','ihd','cvd','hypertension','diabetes','dyslipidemia','baseline_sbp','baseline_dbp','baseline_bmi','baseline_egfr','baseline_hb','baseline_chol','baseline_tg','baseline_ldl','baseline_hdl','baseline_albuminuria','raasi','glp1ra','sglt2i','statin','egfr_slope_ours']
_pipeline=None
_model_load_error=None

def _load_model():
    global _pipeline,_model_load_error
    if _pipeline is not None: return _pipeline
    if _model_load_error is not None: return None
    if not MODEL_FILE.exists():
        _model_load_error=f'Model file not found: {MODEL_FILE}'; return None
    try:
        import joblib
        _pipeline=joblib.load(MODEL_FILE)
        return _pipeline
    except Exception as exc:
        _model_load_error=f'Model could not be loaded: {exc}'; return None

def predict_progression(baseline_data: dict, trend_data: dict) -> dict:
    row={k:baseline_data.get(k) for k in FEATURES}
    row['egfr_slope_ours']=trend_data.get('egfr_slope')
    df=pd.DataFrame([row],columns=FEATURES)
    model=_load_model()
    if model is not None:
        try:
            prob=float(model.predict_proba(df)[0][1])
            risk='HIGH' if prob>=0.35 else ('MEDIUM' if prob>=0.20 else 'LOW')
            return {'risk_level':risk,'probability':round(prob,4),'model_used':'RandomForest training-data prototype','features_df':df,'model_available':True,'notes':[]}
        except Exception as exc:
            model_error=f'Trained model scoring failed: {exc}'
    else:
        model_error=_model_load_error or 'Model unavailable'
    # Transparent fallback: no probability is fabricated. This is a screening rule, not an ML prediction.
    slope=trend_data.get('egfr_slope')
    latest=trend_data.get('latest_egfr')
    if slope is not None and (slope <= -5 or (latest is not None and latest < 30)):
        risk='HIGH'
    elif slope is not None and (slope < -1 or (latest is not None and latest < 60)):
        risk='MEDIUM'
    else:
        risk='UNASSESSED'
    return {'risk_level':risk,'probability':None,'model_used':'transparent trend-based screening fallback','features_df':df,'model_available':False,'notes':[model_error,'No ML probability is reported because the trained model was not available or scoring failed.']}
