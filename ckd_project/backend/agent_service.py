from __future__ import annotations
import json
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from backend.models import Patient, Visit, LabResult, PatientAnalysis
from backend.agents.orchestrator import run_ckd_pipeline

def _num(value):
    if value is None: return None
    try: return float(value)
    except (TypeError,ValueError): return None

def _baseline(patient: Patient) -> dict:
    bool_fields=('ihd','cvd','hypertension','diabetes','dyslipidemia','raasi','glp1ra','sglt2i','statin')
    result={k:_num(getattr(patient,k,None)) for k in ('age_at_baseline','gender','baseline_sbp','baseline_dbp','baseline_bmi','baseline_egfr','baseline_hb','baseline_chol','baseline_tg','baseline_ldl','baseline_hdl','baseline_albuminuria')}
    result['gender']=int(patient.gender) if patient.gender is not None else None
    for key in bool_fields:
        val=getattr(patient,key,None); result[key]=int(bool(val)) if val is not None else None
    return result

def analyze_patient_record(patient_id: str, db: Session) -> dict:
    patient=db.scalar(select(Patient).options(selectinload(Patient.visits).selectinload(Visit.lab_results)).where(Patient.patient_id==patient_id))
    if patient is None: raise ValueError('Patient not found')
    visits=[]
    for visit in sorted(patient.visits,key=lambda v:(v.visit_date or date.min,v.visit_id)):
        labs=sorted(visit.lab_results,key=lambda l:l.lab_result_id)
        if not labs: continue
        lab=labs[-1]
        visits.append({'visit_date':visit.visit_date.isoformat() if visit.visit_date else None,
            'egfr_ml_min_1_73m2':_num(lab.egfr_ml_min_1_73m2),'creatinine_mg_dl':_num(lab.creatinine_mg_dl),
            'acr_mg_g':_num(lab.acr_mg_g),'sbp_mmhg':_num(lab.sbp_mmhg),'dbp_mmhg':_num(lab.dbp_mmhg),
            'hemoglobin_g_dl':_num(lab.hemoglobin_g_dl),'data_source':lab.data_source})
    result=run_ckd_pipeline(_baseline(patient),visits)
    # Keep JSON payload JSON-safe for MySQL JSON columns.
    safe=json.loads(json.dumps(result,default=lambda x: x.isoformat() if hasattr(x,'isoformat') else float(x) if isinstance(x,Decimal) else str(x)))
    trends=safe.get('trends') or {}; priority=safe.get('prioritization') or {}
    analysis=PatientAnalysis(patient_id=patient.patient_id,risk_level=safe.get('risk_level') or 'UNASSESSED',
        probability=safe.get('probability'),model_used=safe.get('model_used'),egfr_trend=safe.get('egfr_trend'),
        egfr_slope=trends.get('egfr_slope'),latest_egfr=trends.get('latest_egfr'),priority=priority.get('priority'),
        priority_score=priority.get('priority_score'),result_json=safe)
    db.add(analysis); db.commit(); db.refresh(analysis)
    safe['analysis_id']=analysis.analysis_id
    safe['created_at']=analysis.created_at.isoformat() if analysis.created_at else None
    return safe
