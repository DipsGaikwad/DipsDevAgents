"""eGFR calculation using the 2021 CKD-EPI creatinine equation (race-free).
This is a calculation aid; clinicians must verify units, demographics and results.
Gender codes used by this project: 1=male, 2=female, 3=other/unknown.
The equation is not applied when sex-specific inputs are unavailable.
"""
from typing import Any

def calculate_egfr_2021(creatinine_mg_dl: Any, age_years: Any, gender_code: Any) -> float | None:
    try:
        scr=float(creatinine_mg_dl); age=float(age_years); gender=int(gender_code)
    except (TypeError, ValueError):
        return None
    if scr <= 0 or not (18 <= age <= 120) or gender not in (1, 2):
        return None
    female = gender == 2
    k = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302
    ratio = scr / k
    egfr = 142.0 * (min(ratio, 1.0) ** alpha) * (max(ratio, 1.0) ** -1.200) * (0.9938 ** age)
    if female:
        egfr *= 1.012
    if egfr <= 0 or egfr > 250:
        return None
    return round(float(egfr), 2)

def fill_missing_egfr(visits: list[dict], baseline_data: dict | None = None) -> tuple[list[dict], list[str]]:
    baseline_data = baseline_data or {}
    age = baseline_data.get('age_at_baseline')
    gender = baseline_data.get('gender')
    out=[]; notes=[]
    for item in visits:
        row=dict(item)
        egfr=row.get('egfr_ml_min_1_73m2')
        if egfr is None or egfr == '':
            value=calculate_egfr_2021(row.get('creatinine_mg_dl'), age, gender)
            if value is not None:
                row['egfr_ml_min_1_73m2']=value
                row['egfr_calculation_method']='CKD-EPI 2021 creatinine equation'
                notes.append(f"Calculated eGFR for visit {row.get('visit_date', 'with no date')} using CKD-EPI 2021.")
        out.append(row)
    return out, notes
