from backend.agents.egfr_agent import calculate_egfr_2021, fill_missing_egfr
from backend.agents.trend_agent import analyze_trends
from backend.agents.orchestrator import run_ckd_pipeline

def baseline():
    return {'age_at_baseline':58,'gender':1,'ihd':0,'cvd':0,'hypertension':1,'diabetes':1,'dyslipidemia':1,'baseline_sbp':145,'baseline_dbp':90,'baseline_bmi':28.5,'baseline_egfr':55,'baseline_hb':13.5,'baseline_chol':210,'baseline_tg':150,'baseline_ldl':130,'baseline_hdl':40,'baseline_albuminuria':150,'raasi':1,'glp1ra':0,'sglt2i':1,'statin':1}

def test_egfr_calculation_requires_valid_inputs():
    assert calculate_egfr_2021(1.3,58,1) is not None
    assert calculate_egfr_2021(1.3,58,3) is None
    assert calculate_egfr_2021(0,58,1) is None

def test_missing_egfr_is_filled_when_inputs_available():
    visits,notes=fill_missing_egfr([{'visit_date':'2022-01-01','egfr_ml_min_1_73m2':None,'creatinine_mg_dl':1.3}],baseline())
    assert visits[0]['egfr_ml_min_1_73m2'] is not None
    assert notes

def test_trend_needs_two_dated_measurements():
    assert analyze_trends([{'visit_date':'2022-01-01','egfr_ml_min_1_73m2':55}])['egfr_slope'] is None
    result=analyze_trends([{'visit_date':'2022-01-01','egfr_ml_min_1_73m2':60},{'visit_date':'2023-01-01','egfr_ml_min_1_73m2':50}])
    assert result['egfr_slope'] < 0

def test_pipeline_returns_agents_and_model_probability():
    result=run_ckd_pipeline(baseline(),[{'visit_date':'2022-01-01','egfr_ml_min_1_73m2':58,'creatinine_mg_dl':1.3},{'visit_date':'2023-01-01','egfr_ml_min_1_73m2':48,'creatinine_mg_dl':1.6}])
    assert result['status']=='success'
    assert result['trends']['measurements_used']==2
    assert 'prioritization' in result
    assert result['risk_level'] in {'HIGH','MEDIUM','LOW','UNASSESSED'}
