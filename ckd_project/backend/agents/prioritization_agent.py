def prioritize_case(prediction: dict, trends: dict) -> dict:
    """Operational triage queue ranking, not a treatment recommendation."""
    risk=str(prediction.get('risk_level','UNASSESSED')).upper()
    latest=trends.get('latest_egfr'); slope=trends.get('egfr_slope')
    reasons=[]; score=0
    if risk=='HIGH': score+=60; reasons.append('High progression-risk category from available analysis.')
    elif risk=='MEDIUM': score+=30; reasons.append('Medium progression-risk category from available analysis.')
    if latest is not None and latest<30: score+=30; reasons.append('Latest recorded eGFR is below 30 mL/min/1.73 m².')
    elif latest is not None and latest<60: score+=15; reasons.append('Latest recorded eGFR is below 60 mL/min/1.73 m².')
    if slope is not None and slope<=-5: score+=25; reasons.append('Estimated eGFR decline is at least 5 mL/min/1.73 m² per year.')
    elif slope is not None and slope<-1: score+=10; reasons.append('Longitudinal eGFR trend is declining.')
    if trends.get('measurements_used',0)<2:
        reasons.append('Limited longitudinal data: clinician review and additional measurements may be needed.')
    priority='URGENT REVIEW' if score>=80 else ('HIGH PRIORITY' if score>=50 else ('ROUTINE REVIEW' if score>0 else 'INSUFFICIENT DATA'))
    return {'priority':priority,'priority_score':min(score,100),'reasons':reasons,'is_clinical_decision':False}
