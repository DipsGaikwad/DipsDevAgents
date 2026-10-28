from datetime import datetime, date
from sqlalchemy import Boolean, Date, DateTime, DECIMAL, Enum, ForeignKey, Index, Integer, String, TIMESTAMP, UniqueConstraint, text, JSON
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base

class User(Base):
    __tablename__='users'
    user_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),primary_key=True,autoincrement=True)
    username: Mapped[str]=mapped_column(String(100),unique=True,nullable=False)
    email: Mapped[str]=mapped_column(String(255),unique=True,nullable=False)
    password_hash: Mapped[str]=mapped_column(String(255),nullable=False)
    role: Mapped[str]=mapped_column(Enum('ADMIN','DOCTOR','DEO'),nullable=False,server_default='DOCTOR')
    full_name: Mapped[str|None]=mapped_column(String(150))
    account_status: Mapped[str]=mapped_column(Enum('PENDING','APPROVED','REJECTED','SUSPENDED'),nullable=False,server_default='PENDING')
    approved_by: Mapped[int|None]=mapped_column(BIGINT(unsigned=True),ForeignKey('users.user_id',ondelete='SET NULL'))
    approved_at: Mapped[datetime|None]=mapped_column(DateTime)
    created_at: Mapped[datetime|None]=mapped_column(TIMESTAMP,server_default=text('CURRENT_TIMESTAMP'))

class Patient(Base):
    __tablename__='patients'
    patient_id: Mapped[str]=mapped_column(String(20),primary_key=True)
    full_name: Mapped[str|None]=mapped_column(String(150))
    source_code: Mapped[str]=mapped_column(String(10),nullable=False)
    source_patient_id: Mapped[str]=mapped_column(String(100),nullable=False)
    age_at_baseline: Mapped[float|None]=mapped_column(DECIMAL(5,2))
    gender: Mapped[int|None]=mapped_column(Integer)
    ihd: Mapped[bool|None]=mapped_column(Boolean); cvd: Mapped[bool|None]=mapped_column(Boolean)
    hypertension: Mapped[bool|None]=mapped_column(Boolean); diabetes: Mapped[bool|None]=mapped_column(Boolean)
    dyslipidemia: Mapped[bool|None]=mapped_column(Boolean)
    baseline_sbp: Mapped[float|None]=mapped_column(DECIMAL(6,2)); baseline_dbp: Mapped[float|None]=mapped_column(DECIMAL(6,2))
    baseline_bmi: Mapped[float|None]=mapped_column(DECIMAL(6,2)); baseline_egfr: Mapped[float|None]=mapped_column(DECIMAL(7,2))
    baseline_hb: Mapped[float|None]=mapped_column(DECIMAL(6,2)); baseline_chol: Mapped[float|None]=mapped_column(DECIMAL(7,2))
    baseline_tg: Mapped[float|None]=mapped_column(DECIMAL(7,2)); baseline_ldl: Mapped[float|None]=mapped_column(DECIMAL(7,2)); baseline_hdl: Mapped[float|None]=mapped_column(DECIMAL(7,2))
    baseline_albuminuria: Mapped[int|None]=mapped_column(Integer)
    raasi: Mapped[bool|None]=mapped_column(Boolean); glp1ra: Mapped[bool|None]=mapped_column(Boolean); sglt2i: Mapped[bool|None]=mapped_column(Boolean); statin: Mapped[bool|None]=mapped_column(Boolean)
    created_at: Mapped[datetime|None]=mapped_column(TIMESTAMP,server_default=text('CURRENT_TIMESTAMP'))
    visits: Mapped[list['Visit']]=relationship(back_populates='patient',cascade='all, delete-orphan',passive_deletes=True,order_by='Visit.visit_date')

class Visit(Base):
    __tablename__='visits'
    __table_args__=(UniqueConstraint('patient_id','day_from_baseline',name='uq_patient_day'),Index('idx_patient_day','patient_id','day_from_baseline'))
    visit_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),primary_key=True,autoincrement=True)
    patient_id: Mapped[str]=mapped_column(String(20),ForeignKey('patients.patient_id',ondelete='CASCADE'),nullable=False)
    visit_number: Mapped[int]=mapped_column(Integer,nullable=False)
    day_from_baseline: Mapped[int]=mapped_column(Integer,nullable=False)
    visit_date: Mapped[date|None]=mapped_column(Date)
    encounter_type: Mapped[str|None]=mapped_column(String(50))
    patient: Mapped['Patient']=relationship(back_populates='visits')
    lab_results: Mapped[list['LabResult']]=relationship(back_populates='visit',cascade='all, delete-orphan',passive_deletes=True)

class LabResult(Base):
    __tablename__='lab_results'
    lab_result_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),primary_key=True,autoincrement=True)
    visit_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),ForeignKey('visits.visit_id',ondelete='CASCADE'),nullable=False,index=True)
    creatinine_mg_dl: Mapped[float|None]=mapped_column(DECIMAL(7,3)); egfr_ml_min_1_73m2: Mapped[float|None]=mapped_column(DECIMAL(7,2)); acr_mg_g: Mapped[float|None]=mapped_column(DECIMAL(10,2))
    sbp_mmhg: Mapped[float|None]=mapped_column(DECIMAL(6,2)); dbp_mmhg: Mapped[float|None]=mapped_column(DECIMAL(6,2)); hemoglobin_g_dl: Mapped[float|None]=mapped_column(DECIMAL(6,2))
    hba1c_percent: Mapped[float|None]=mapped_column(DECIMAL(5,2)); glucose_mg_dl: Mapped[float|None]=mapped_column(DECIMAL(7,2)); cholesterol_mg_dl: Mapped[float|None]=mapped_column(DECIMAL(7,2))
    triglycerides_mg_dl: Mapped[float|None]=mapped_column(DECIMAL(7,2)); ldl_mg_dl: Mapped[float|None]=mapped_column(DECIMAL(7,2)); hdl_mg_dl: Mapped[float|None]=mapped_column(DECIMAL(7,2))
    potassium_mmol_l: Mapped[float|None]=mapped_column(DECIMAL(6,2)); sodium_mmol_l: Mapped[float|None]=mapped_column(DECIMAL(6,2)); albumin_g_dl: Mapped[float|None]=mapped_column(DECIMAL(6,2))
    data_source: Mapped[str]=mapped_column(String(20),nullable=False,server_default='REAL')
    visit: Mapped['Visit']=relationship(back_populates='lab_results')

class ProgressionLabel(Base):
    __tablename__='progression_labels'
    progression_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),primary_key=True,autoincrement=True)
    patient_id: Mapped[str]=mapped_column(String(20),ForeignKey('patients.patient_id',ondelete='CASCADE'),nullable=False,unique=True)
    published_egfr_rate: Mapped[float|None]=mapped_column(DECIMAL(7,3)); egfr_slope_ours: Mapped[float|None]=mapped_column(DECIMAL(7,3))
    rapid_progression: Mapped[bool]=mapped_column(Boolean,nullable=False); target_definition: Mapped[str]=mapped_column("target_defination", String(255), nullable=False)

class Notification(Base):
    __tablename__='notifications'
    notification_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),primary_key=True,autoincrement=True)
    user_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),ForeignKey('users.user_id',ondelete='CASCADE'),nullable=False,index=True)
    patient_id: Mapped[str|None]=mapped_column(String(20),ForeignKey('patients.patient_id',ondelete='SET NULL'),nullable=True)
    title: Mapped[str]=mapped_column(String(180),nullable=False); message: Mapped[str]=mapped_column(String(1000),nullable=False)
    notification_type: Mapped[str]=mapped_column(String(50),nullable=False,server_default='SYSTEM')
    is_read: Mapped[bool]=mapped_column(Boolean,nullable=False,server_default=text('0'))
    created_at: Mapped[datetime]=mapped_column(TIMESTAMP,server_default=text('CURRENT_TIMESTAMP'))

class KnowledgeResource(Base):
    __tablename__='knowledge_resources'
    resource_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),primary_key=True,autoincrement=True)
    title: Mapped[str]=mapped_column(String(255),nullable=False); category: Mapped[str]=mapped_column(String(80),nullable=False)
    source_name: Mapped[str|None]=mapped_column(String(255)); source_url: Mapped[str|None]=mapped_column(String(1000)); version_label: Mapped[str|None]=mapped_column(String(100))
    original_filename: Mapped[str]=mapped_column(String(255),nullable=False); stored_filename: Mapped[str]=mapped_column(String(255),unique=True,nullable=False)
    mime_type: Mapped[str]=mapped_column(String(100),nullable=False); file_size_bytes: Mapped[int]=mapped_column(BIGINT(unsigned=True),nullable=False)
    uploaded_by: Mapped[int]=mapped_column(BIGINT(unsigned=True),ForeignKey('users.user_id'),nullable=False)
    status: Mapped[str]=mapped_column(Enum('UPLOADED','PROCESSING','INDEXED','FAILED'),nullable=False,server_default='UPLOADED')
    created_at: Mapped[datetime]=mapped_column(TIMESTAMP,server_default=text('CURRENT_TIMESTAMP'))

class ProfileSetting(Base):
    __tablename__='user_profile_settings'
    user_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),ForeignKey('users.user_id',ondelete='CASCADE'),primary_key=True)
    hospital: Mapped[str|None]=mapped_column(String(255))


class PatientAnalysis(Base):
    __tablename__='patient_analyses'
    analysis_id: Mapped[int]=mapped_column(BIGINT(unsigned=True),primary_key=True,autoincrement=True)
    patient_id: Mapped[str]=mapped_column(String(20),ForeignKey('patients.patient_id',ondelete='CASCADE'),nullable=False,index=True)
    risk_level: Mapped[str]=mapped_column(String(30),nullable=False,server_default='UNASSESSED')
    probability: Mapped[float|None]=mapped_column(DECIMAL(8,6))
    model_used: Mapped[str|None]=mapped_column(String(120))
    egfr_trend: Mapped[str|None]=mapped_column(String(80))
    egfr_slope: Mapped[float|None]=mapped_column(DECIMAL(9,3))
    latest_egfr: Mapped[float|None]=mapped_column(DECIMAL(8,2))
    priority: Mapped[str|None]=mapped_column(String(40))
    priority_score: Mapped[int|None]=mapped_column(Integer)
    result_json: Mapped[dict|None]=mapped_column(JSON)
    created_at: Mapped[datetime|None]=mapped_column(TIMESTAMP,server_default=text('CURRENT_TIMESTAMP'))
