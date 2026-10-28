from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend.auth import require_roles
from backend.database import get_db
from backend.models import (
    LabResult,
    Notification,
    Patient,
    PatientAnalysis,
    ProgressionLabel,
    User,
    Visit,
)
from backend.schemas import PatientCreate, VisitCreate
from backend.agents.egfr_agent import calculate_egfr_2021
from backend.agent_service import analyze_patient_record


router = APIRouter(tags=["Patients and visits"])


def patient_query():
    return select(Patient).options(
        selectinload(Patient.visits).selectinload(Visit.lab_results)
    )


def patient_to_dict(p: Patient, db: Session):
    label = db.scalar(
        select(ProgressionLabel).where(
            ProgressionLabel.patient_id == p.patient_id
        )
    )
    analysis = db.scalar(
        select(PatientAnalysis)
        .where(PatientAnalysis.patient_id == p.patient_id)
        .order_by(
            PatientAnalysis.created_at.desc(),
            PatientAnalysis.analysis_id.desc(),
        )
        .limit(1)
    )

    return {
        "patient_id": p.patient_id,
        "full_name": p.full_name,
        "source_code": p.source_code,
        "source_patient_id": p.source_patient_id,
        "age_at_baseline": p.age_at_baseline,
        "gender": p.gender,
        "ihd": p.ihd,
        "cvd": p.cvd,
        "hypertension": p.hypertension,
        "diabetes": p.diabetes,
        "dyslipidemia": p.dyslipidemia,
        "baseline_sbp": p.baseline_sbp,
        "baseline_dbp": p.baseline_dbp,
        "baseline_bmi": p.baseline_bmi,
        "baseline_egfr": p.baseline_egfr,
        "baseline_hb": p.baseline_hb,
        "baseline_chol": p.baseline_chol,
        "baseline_tg": p.baseline_tg,
        "baseline_ldl": p.baseline_ldl,
        "baseline_hdl": p.baseline_hdl,
        "baseline_albuminuria": p.baseline_albuminuria,
        "raasi": p.raasi,
        "glp1ra": p.glp1ra,
        "sglt2i": p.sglt2i,
        "statin": p.statin,
        "latest_analysis": (
            {
                "risk_level": analysis.risk_level,
                "probability": (
                    float(analysis.probability)
                    if analysis.probability is not None
                    else None
                ),
                "model_used": analysis.model_used,
                "egfr_trend": analysis.egfr_trend,
                "egfr_slope_ours": (
                    float(analysis.egfr_slope)
                    if analysis.egfr_slope is not None
                    else None
                ),
                "priority": analysis.priority,
                "priority_score": analysis.priority_score,
                "created_at": analysis.created_at,
            }
            if analysis
            else (
                {
                    "risk_level": "HIGH" if label.rapid_progression else "LOW",
                    "probability": None,
                    "target_definition": label.target_definition,
                    "egfr_slope_ours": label.egfr_slope_ours,
                }
                if label
                else None
            )
        ),
        "visits": [
            {
                "visit_id": v.visit_id,
                "visit_number": v.visit_number,
                "day_from_baseline": v.day_from_baseline,
                "visit_date": v.visit_date,
                "encounter_type": v.encounter_type,
                "lab_results": [
                    {
                        "lab_result_id": lab.lab_result_id,
                        "creatinine_mg_dl": lab.creatinine_mg_dl,
                        "egfr_ml_min_1_73m2": lab.egfr_ml_min_1_73m2,
                        "acr_mg_g": lab.acr_mg_g,
                        "sbp_mmhg": lab.sbp_mmhg,
                        "dbp_mmhg": lab.dbp_mmhg,
                        "hemoglobin_g_dl": lab.hemoglobin_g_dl,
                        "hba1c_percent": lab.hba1c_percent,
                        "glucose_mg_dl": lab.glucose_mg_dl,
                        "cholesterol_mg_dl": lab.cholesterol_mg_dl,
                        "triglycerides_mg_dl": lab.triglycerides_mg_dl,
                        "ldl_mg_dl": lab.ldl_mg_dl,
                        "hdl_mg_dl": lab.hdl_mg_dl,
                        "potassium_mmol_l": lab.potassium_mmol_l,
                        "sodium_mmol_l": lab.sodium_mmol_l,
                        "albumin_g_dl": lab.albumin_g_dl,
                        "data_source": lab.data_source,
                    }
                    for lab in v.lab_results
                ],
            }
            for v in sorted(
                p.visits,
                key=lambda visit: (visit.visit_date or date.min, visit.visit_id),
            )
        ],
    }


@router.get("/patients")
def list_patients(
    search: str | None = None,
    source_code: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "DOCTOR", "DEO")),
):
    q = patient_query().order_by(Patient.patient_id)
    if search:
        q = q.where(
            or_(
                Patient.patient_id.like(f"%{search}%"),
                Patient.full_name.like(f"%{search}%"),
                Patient.source_patient_id.like(f"%{search}%"),
            )
        )
    if source_code:
        q = q.where(Patient.source_code == source_code)

    rows = db.scalars(q.offset(offset).limit(limit)).unique().all()
    return {
        "items": [patient_to_dict(patient, db) for patient in rows],
        "count": len(rows),
        "limit": limit,
        "offset": offset,
    }


@router.post("/patients", status_code=201)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "DOCTOR", "DEO")),
):
    # Generate a readable application ID when the caller leaves it blank.
    requested_id = (getattr(payload, "patient_id", None) or "").strip()
    if not requested_id:
        existing_ids = db.scalars(select(Patient.patient_id)).all()
        highest = 0
        for existing_id in existing_ids:
            if existing_id and existing_id.startswith("CKD-"):
                try:
                    highest = max(highest, int(existing_id.split("-", 1)[1]))
                except ValueError:
                    continue
        requested_id = f"CKD-{highest + 1:06d}"

    if db.get(Patient, requested_id):
        raise HTTPException(
            status_code=409,
            detail="Patient ID already exists. Please retry patient creation.",
        )

    source_id = (getattr(payload, "source_patient_id", None) or "").strip()
    source_code = payload.source_code
    if not source_id:
        existing_source_ids = db.scalars(
            select(Patient.source_patient_id).where(
                Patient.source_code == source_code
            )
        ).all()
        prefix = f"{source_code}-SRC-"
        highest_source = 0
        for value in existing_source_ids:
            if value and value.startswith(prefix):
                try:
                    highest_source = max(
                        highest_source, int(value[len(prefix):])
                    )
                except ValueError:
                    continue
        source_id = f"{prefix}{highest_source + 1:06d}"

    duplicate_source = db.scalar(
        select(Patient).where(
            Patient.source_code == source_code,
            Patient.source_patient_id == source_id,
        )
    )
    if duplicate_source:
        raise HTTPException(
            status_code=409,
            detail="This source code/source patient ID is already registered.",
        )

    data = payload.model_dump()
    data["patient_id"] = requested_id
    data["source_patient_id"] = source_id
    patient = Patient(**data)
    db.add(patient)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not save patient because an identifier already exists. Retry creation.",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Could not save patient."
        ) from exc

    return {
        "message": "Patient created",
        "patient_id": patient.patient_id,
        "source_patient_id": patient.source_patient_id,
    }


@router.get("/patients/{patient_id}")
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "DOCTOR", "DEO")),
):
    patient = db.scalar(patient_query().where(Patient.patient_id == patient_id))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient_to_dict(patient, db)


@router.put("/patients/{patient_id}")
def update_patient(
    patient_id: str,
    payload: PatientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "DOCTOR", "DEO")),
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    payload_patient_id = getattr(payload, "patient_id", None)
    if payload_patient_id and payload_patient_id != patient_id:
        raise HTTPException(status_code=422, detail="Patient ID cannot be changed")

    data = payload.model_dump(exclude_unset=True)
    # IDs are generated/assigned at creation and should not be silently replaced.
    data.pop("patient_id", None)
    data.pop("source_patient_id", None)
    for key, value in data.items():
        setattr(patient, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not update patient because a unique identifier conflicts.",
        ) from exc
    return {"message": "Patient updated"}


@router.delete("/patients/{patient_id}", status_code=204)
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "DOCTOR")),
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()
    return None


@router.post("/patients/{patient_id}/visits", status_code=201)
def add_visit(
    patient_id: str,
    payload: VisitCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "DOCTOR", "DEO")),
):
    patient = db.scalar(
        select(Patient)
        .options(selectinload(Patient.visits))
        .where(Patient.patient_id == patient_id)
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # A patient can have at most one visit per calendar date in this schema.
    existing_same_date = db.scalar(
        select(Visit).where(
            Visit.patient_id == patient_id,
            Visit.visit_date == payload.visit_date,
        )
    )
    if existing_same_date:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A visit already exists for this patient on "
                f"{payload.visit_date.isoformat()}. Choose another date or edit "
                "the existing visit."
            ),
        )

    # Keep day_from_baseline unique even when an older-dated visit is added later.
    # This project schema has no separate patient baseline-date column, so the
    # earliest visit date is treated as day 0. If the new visit predates the
    # current earliest visit, shift the stored offsets to maintain that rule.
    dated_visits = [v for v in patient.visits if v.visit_date is not None]
    if dated_visits:
        old_first_date = min(v.visit_date for v in dated_visits)
        if payload.visit_date < old_first_date:
            # Shift all existing offsets by the same positive delta. This
            # preserves their relative spacing and avoids transient collisions
            # with the unique (patient_id, day_from_baseline) index.
            shift_days = (old_first_date - payload.visit_date).days
            for old_visit in dated_visits:
                old_visit.day_from_baseline = (
                    old_visit.day_from_baseline + shift_days
                )
            first_date = payload.visit_date
        else:
            first_date = old_first_date
    else:
        first_date = payload.visit_date

    day_offset = (payload.visit_date - first_date).days

    # Use the next visit number. It records entry order; the date/offset records
    # chronology. Do not use visit_number as the day offset.
    next_visit_number = max(
        (v.visit_number or 0 for v in patient.visits), default=0
    ) + 1

    lab_data = payload.labs.model_dump(exclude_unset=True)
    if lab_data.get("egfr_ml_min_1_73m2") is None:
        calculated = calculate_egfr_2021(
            lab_data.get("creatinine_mg_dl"),
            patient.age_at_baseline,
            patient.gender,
        )
        if calculated is not None:
            lab_data["egfr_ml_min_1_73m2"] = calculated
            lab_data["data_source"] = "CALCULATED"

    visit = Visit(
        patient_id=patient_id,
        visit_number=next_visit_number,
        day_from_baseline=day_offset,
        visit_date=payload.visit_date,
        encounter_type=payload.encounter_type,
    )
    db.add(visit)

    try:
        # Flush the visit so its generated visit_id is available for LabResult.
        db.flush()
        db.add(LabResult(visit_id=visit.visit_id, **lab_data))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "The visit conflicts with an existing patient/date or "
                "patient/day record. No visit or lab data were saved. "
                "Check the existing visits and try again."
            ),
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save visit and laboratory data.",
        ) from exc

    db.refresh(visit)

    # Analysis is best-effort: a model/agent failure must not undo the saved visit.
    try:
        analysis_result = analyze_patient_record(patient_id, db)
    except Exception as exc:
        analysis_result = {
            "status": "analysis_unavailable",
            "message": (
                "The visit was saved, but the agent analysis could not be completed."
            ),
        }

    return {
        "message": "Visit and laboratory record created",
        "visit_id": visit.visit_id,
        "visit_number": visit.visit_number,
        "day_from_baseline": visit.day_from_baseline,
        "analysis": analysis_result,
    }


@router.get("/visits")
def list_visits(
    patient_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "DOCTOR", "DEO")),
):
    q = (
        select(Visit)
        .options(selectinload(Visit.patient), selectinload(Visit.lab_results))
        .order_by(Visit.visit_date.desc())
    )
    if patient_id:
        q = q.where(Visit.patient_id == patient_id)

    rows = db.scalars(q.limit(2000)).unique().all()
    return {
        "items": [
            {
                "visit_id": visit.visit_id,
                "patient_id": visit.patient_id,
                "patient_name": (
                    visit.patient.full_name or visit.patient.patient_id
                ),
                "visit_number": visit.visit_number,
                "visit_date": visit.visit_date,
                "day_from_baseline": visit.day_from_baseline,
                "encounter_type": visit.encounter_type,
                "lab_results": [
                    {
                        "egfr_ml_min_1_73m2": lab.egfr_ml_min_1_73m2,
                        "creatinine_mg_dl": lab.creatinine_mg_dl,
                        "acr_mg_g": lab.acr_mg_g,
                        "sbp_mmhg": lab.sbp_mmhg,
                        "dbp_mmhg": lab.dbp_mmhg,
                        "hemoglobin_g_dl": lab.hemoglobin_g_dl,
                        "potassium_mmol_l": lab.potassium_mmol_l,
                    }
                    for lab in visit.lab_results
                ],
            }
            for visit in rows
        ]
    }


@router.post("/patients/{patient_id}/analyze")
def analyze_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "DOCTOR")),
):
    try:
        return analyze_patient_record(patient_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Analysis could not be completed or saved.",
        ) from exc
