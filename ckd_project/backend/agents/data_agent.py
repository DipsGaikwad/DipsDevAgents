from datetime import date, datetime
import math
import pandas as pd

def validate_patient_data(visits: list) -> dict:
    issues=[]
    if not visits:
        return {'status':'INVALID','issues':['No visit records provided.']}
    parsed=[]
    for i, visit in enumerate(visits, start=1):
        raw_date=visit.get('visit_date')
        try:
            parsed.append(pd.to_datetime(raw_date, errors='raise'))
        except Exception:
            issues.append(f'Visit {i} has an invalid or missing visit date.')
        egfr=visit.get('egfr_ml_min_1_73m2')
        if egfr is None or egfr == '':
            issues.append(f'Visit {i} has no eGFR value; calculation may not have been possible.')
            continue
        try: value=float(egfr)
        except (TypeError,ValueError):
            issues.append(f'Visit {i} eGFR is not numeric.'); continue
        if not math.isfinite(value) or value <= 0 or value > 250:
            issues.append(f'Visit {i} has an implausible eGFR value ({value}).')
    if len(parsed)==len(visits):
        if parsed != sorted(parsed): issues.append('Visit dates were not chronological; records were sorted before trend analysis.')
        if len(set(parsed)) != len(parsed): issues.append('Duplicate visit dates detected.')
    hard=any('invalid or missing visit date' in x or 'not numeric' in x or 'implausible' in x or 'Duplicate' in x for x in issues)
    status='INVALID' if hard else ('PARTIAL' if issues else 'VALID')
    return {'status':status,'issues':issues}


def validate_and_prepare_patient_data(visits: list, baseline_data: dict | None = None) -> dict:
    """Data agent: fill calculable missing eGFR values, then validate the prepared history."""
    from backend.agents.egfr_agent import fill_missing_egfr
    prepared, notes = fill_missing_egfr(visits or [], baseline_data or {})
    validation = validate_patient_data(prepared)
    return {
        "visits": prepared,
        "calculation_notes": notes,
        "status": validation["status"],
        "issues": validation["issues"],
    }
