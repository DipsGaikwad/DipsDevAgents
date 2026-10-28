"""LangGraph orchestration for the CKD progression review pipeline."""
from typing import TypedDict, List, Dict, Any
from backend.agents.data_agent import validate_and_prepare_patient_data
from backend.agents.trend_agent import analyze_trends
from backend.agents.prediction_agent import predict_progression, _load_model
from backend.agents.explanation_agent import explain_prediction
from backend.agents.prioritization_agent import prioritize_case

class CKDState(TypedDict, total=False):
    baseline_data: Dict[str, Any]
    visits: List[Dict[str, Any]]
    validation_status: str
    issues: List[str]
    calculation_notes: List[str]
    trends: Dict[str, Any]
    prediction: Dict[str, Any]
    features_df: Any
    explanations: List[Dict[str, Any]]
    prioritization: Dict[str, Any]

def data_validator_node(state: CKDState) -> dict:
    # eGFR calculation is deliberately embedded in the Data Validation Agent.
    result = validate_and_prepare_patient_data(
        state.get('visits') or [], state.get('baseline_data') or {}
    )
    return {
        'visits': result['visits'],
        'calculation_notes': result['calculation_notes'],
        'validation_status': result['status'],
        'issues': result['issues'],
    }

def trend_analyzer_node(state: CKDState) -> dict:
    return {'trends': analyze_trends(state.get('visits') or [])}

def prediction_node(state: CKDState) -> dict:
    result = predict_progression(state.get('baseline_data') or {}, state.get('trends') or {})
    return {'prediction': {k:v for k,v in result.items() if k != 'features_df'}, 'features_df': result.get('features_df')}

def explanation_node(state: CKDState) -> dict:
    pred=state.get('prediction') or {}
    df=state.get('features_df')
    if pred.get('model_available') and df is not None:
        explanations=explain_prediction(df,_load_model())
    else:
        explanations=explain_prediction(df,None)
    return {'explanations': explanations}

def prioritization_node(state: CKDState) -> dict:
    return {'prioritization': prioritize_case(state.get('prediction') or {}, state.get('trends') or {})}

def _finish_invalid_node(state: CKDState) -> dict:
    return {
        'trends': {'egfr_slope': None, 'egfr_trend': 'not calculated because validation failed', 'measurements_used': 0, 'latest_egfr': None},
        'prediction': {'risk_level':'UNASSESSED','probability':None,'model_used':'not run','model_available':False,'notes':['Validation failed; prediction was not run.']},
        'explanations': [],
        'prioritization': {'priority':'INSUFFICIENT DATA','priority_score':0,'reasons':state.get('issues') or ['Validation failed.'],'is_clinical_decision':False}
    }

def _route_validation(state: CKDState) -> str:
    return 'invalid' if state.get('validation_status') == 'INVALID' else 'valid'

try:
    from langgraph.graph import StateGraph, END
    graph=StateGraph(CKDState)
    graph.add_node('data_validator', data_validator_node)
    graph.add_node('trend_analyzer', trend_analyzer_node)
    graph.add_node('progression_predictor', prediction_node)
    graph.add_node('shap_explainer', explanation_node)
    graph.add_node('prioritization', prioritization_node)
    graph.add_node('validation_failed', _finish_invalid_node)
    graph.set_entry_point('data_validator')
    graph.add_conditional_edges('data_validator',_route_validation,{'valid':'trend_analyzer','invalid':'validation_failed'})
    graph.add_edge('trend_analyzer','progression_predictor')
    graph.add_edge('progression_predictor','shap_explainer')
    graph.add_edge('shap_explainer','prioritization')
    graph.add_edge('prioritization',END)
    graph.add_edge('validation_failed',END)
    ckd_graph=graph.compile()
except ImportError:
    ckd_graph=None

def _run_steps(initial: dict) -> dict:
    state=dict(initial)
    state.update(data_validator_node(state))
    if state.get('validation_status') == 'INVALID':
        state.update(_finish_invalid_node(state))
        return state
    state.update(trend_analyzer_node(state))
    state.update(prediction_node(state))
    state.update(explanation_node(state))
    state.update(prioritization_node(state))
    return state

def run_ckd_pipeline(baseline_data: dict, visits: list) -> dict:
    initial={'baseline_data':baseline_data or {},'visits':visits or []}
    try:
        state=ckd_graph.invoke(initial) if ckd_graph is not None else _run_steps(initial)
    except Exception as exc:
        return {'status':'error','error':'Pipeline failed','details':str(exc),'risk_level':'UNASSESSED','probability':None}
    pred=state.get('prediction') or {}; trends=state.get('trends') or {}
    return {
        'status':'success' if state.get('validation_status')!='INVALID' else 'validation_failed',
        'validation_status':state.get('validation_status'),'validation_issues':state.get('issues',[]),
        'calculation_notes':state.get('calculation_notes',[]),'risk_level':pred.get('risk_level','UNASSESSED'),
        'probability':pred.get('probability'),'model_used':pred.get('model_used'),'model_available':pred.get('model_available',False),
        'model_notes':pred.get('notes',[]),'egfr_trend':trends.get('egfr_trend','unknown'),
        'trends':trends,'top_factors':state.get('explanations',[]),
        'prioritization':state.get('prioritization',{}),'visits_with_egfr':state.get('visits',[])
    }
