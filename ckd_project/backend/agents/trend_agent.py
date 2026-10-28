import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

def analyze_trends(visits: list) -> dict:
    if not visits:
        return {'egfr_slope':None,'egfr_trend':'unknown','measurements_used':0,'latest_egfr':None,'first_egfr':None}
    df=pd.DataFrame(visits)
    if 'visit_date' not in df or 'egfr_ml_min_1_73m2' not in df:
        return {'egfr_slope':None,'egfr_trend':'unknown','measurements_used':0,'latest_egfr':None,'first_egfr':None}
    df['visit_date']=pd.to_datetime(df['visit_date'],errors='coerce')
    df['egfr_ml_min_1_73m2']=pd.to_numeric(df['egfr_ml_min_1_73m2'],errors='coerce')
    df=df.dropna(subset=['visit_date','egfr_ml_min_1_73m2']).sort_values('visit_date')
    if df.empty:
        return {'egfr_slope':None,'egfr_trend':'unknown','measurements_used':0,'latest_egfr':None,'first_egfr':None}
    first=float(df.iloc[0]['egfr_ml_min_1_73m2']); latest=float(df.iloc[-1]['egfr_ml_min_1_73m2'])
    if len(df)<2 or df['visit_date'].nunique()<2:
        return {'egfr_slope':None,'egfr_trend':'insufficient longitudinal data','measurements_used':len(df),'latest_egfr':round(latest,2),'first_egfr':round(first,2)}
    days=(df['visit_date']-df['visit_date'].iloc[0]).dt.days.to_numpy(dtype=float).reshape(-1,1)
    model=LinearRegression().fit(days,df['egfr_ml_min_1_73m2'].to_numpy(dtype=float))
    slope=float(model.coef_[0]*365.25)
    trend='rapid decline' if slope <= -5 else ('declining' if slope < -1 else ('approximately stable' if slope <= 1 else 'increasing'))
    return {'egfr_slope':round(slope,3),'egfr_trend':trend,'measurements_used':len(df),'latest_egfr':round(latest,2),'first_egfr':round(first,2),'observation_period_days':int((df['visit_date'].iloc[-1]-df['visit_date'].iloc[0]).days)}
