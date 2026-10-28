"""Best-effort feature explanations; never fail the complete analysis if SHAP is unavailable."""
import numpy as np

def explain_prediction(features_df, model=None) -> list[dict]:
    if model is None:
        return [{'feature':'eGFR trend','impact':None,'direction':'requires clinician review','note':'No compatible trained model is available for SHAP explanations.'}]
    try:
        import shap
        classifier=model.named_steps.get('classifier',model)
        transformed=features_df
        if 'imputer' in getattr(model,'named_steps',{}):
            transformed=model.named_steps['imputer'].transform(features_df)
        explainer=shap.TreeExplainer(classifier)
        values=explainer.shap_values(transformed)
        if isinstance(values,list): vals=np.asarray(values[-1])[0]
        else:
            arr=np.asarray(values)
            if arr.ndim==3: vals=arr[0,:,1] if arr.shape[-1]>1 else arr[0,:,0]
            elif arr.ndim==2: vals=arr[0]
            else: vals=arr.reshape(-1)
        names=list(features_df.columns)
        ranked=np.argsort(np.abs(vals))[::-1][:5]
        return [{'feature':names[int(i)],'impact':round(float(vals[int(i)]),5),'direction':'increases model score' if vals[int(i)]>0 else 'decreases model score'} for i in ranked]
    except Exception as exc:
        return [{'feature':'explanation','impact':None,'direction':'unavailable','note':f'SHAP explanation could not be generated: {exc}'}]
