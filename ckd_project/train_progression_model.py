"""Rebuild the prototype progression model from the included processed cohort."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'processed'/'ml_dataset.csv'
OUT=ROOT/'models'/'trained'
FEATURES=['age_at_baseline','gender','ihd','cvd','hypertension','diabetes','dyslipidemia','baseline_sbp','baseline_dbp','baseline_bmi','baseline_egfr','baseline_hb','baseline_chol','baseline_tg','baseline_ldl','baseline_hdl','baseline_albuminuria','raasi','glp1ra','sglt2i','statin','egfr_slope_ours']

def main():
    df=pd.read_csv(DATA).dropna(subset=['rapid_progression'])
    X=df[FEATURES].replace([np.inf,-np.inf],np.nan); y=df['rapid_progression'].astype(int)
    X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=.2,random_state=42,stratify=y)
    model=Pipeline([('imputer',SimpleImputer(strategy='median',keep_empty_features=True)),('classifier',RandomForestClassifier(n_estimators=250,min_samples_leaf=2,class_weight='balanced_subsample',random_state=42,n_jobs=-1))])
    model.fit(X_train,y_train)
    prob=model.predict_proba(X_test)[:,1]; threshold=.30; pred=(prob>=threshold).astype(int)
    metrics={'scikit_learn_version':sklearn.__version__,'dataset_rows':int(len(df)),'train_rows':int(len(X_train)),'test_rows':int(len(X_test)),'positive_label_count':int(y.sum()),'evaluation_threshold':threshold,'roc_auc':round(float(roc_auc_score(y_test,prob)),4),'accuracy_at_threshold':round(float(accuracy_score(y_test,pred)),4),'precision_at_threshold':round(float(precision_score(y_test,pred,zero_division=0)),4),'recall_at_threshold':round(float(recall_score(y_test,pred,zero_division=0)),4),'f1_at_threshold':round(float(f1_score(y_test,pred,zero_division=0)),4),'confusion_matrix_tn_fp_fn_tp':confusion_matrix(y_test,pred).ravel().tolist(),'label_definition_note':'rapid_progression label as provided in included processed cohort; verify original label definition before clinical interpretation','caveat':'Single random holdout only; possible target/feature relationship with egfr_slope_ours; not externally validated and not for clinical use.'}
    OUT.mkdir(parents=True,exist_ok=True); joblib.dump(model,OUT/'ckd_model.joblib'); (OUT/'training_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2))
if __name__=='__main__': main()
