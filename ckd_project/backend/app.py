from datetime import datetime
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text, or_
from sqlalchemy.orm import Session
from backend.config import settings, allowed_origins
from backend.database import get_db
from backend.models import User, Notification, ProfileSetting
from backend.schemas import RegisterRequest, LoginRequest, StatusUpdate, ProfileUpdate, PatientRequest, PredictionResponse
from backend.auth import hash_password, verify_password, create_token, get_current_user, require_roles
from backend.patients import router as patients_router
from backend.resources import router as resources_router
from backend.reports import router as reports_router
from backend.clinical_assistant import router as clinical_assistant_router
from backend.password_reset import router as password_reset_router
app=FastAPI(title='CKD Care API',version='1.1.0',description='MySQL-backed CKD Care student prototype. RAG is intentionally deferred.')
app.add_middleware(CORSMiddleware,allow_origins=allowed_origins(),allow_credentials=True,allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type'])
app.include_router(patients_router); app.include_router(resources_router); app.include_router(reports_router); app.include_router(clinical_assistant_router);
app.include_router(password_reset_router);
@app.get('/')
def root(): return {'message':'CKD Care API is running','database':'configured','rag':'deferred'}
@app.get('/health')
def health(db:Session=Depends(get_db)):
    db.execute(text('SELECT 1'))
    return {'status':'ok','database':'connected'}

@app.post('/auth/register',status_code=201)
def register(payload:RegisterRequest,db:Session=Depends(get_db)):
    if db.scalar(select(User).where(or_(User.username==payload.username,User.email==str(payload.email)))):
        raise HTTPException(status_code=409,detail='Username or email already registered')
    user=User(username=payload.username,email=str(payload.email),password_hash=hash_password(payload.password),role=payload.role,full_name=payload.full_name,account_status='PENDING')
    db.add(user)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(status_code=409,detail='Registration failed. Check whether users table has the required role/status/name columns.') from exc
    return {'message':'Account created. An Admin must approve it before sign-in.','user_id':user.user_id,'account_status':'PENDING'}

@app.post('/auth/login')
def login(payload:LoginRequest,db:Session=Depends(get_db)):
    identity=(payload.username or '').strip()
    if payload.email: identity=str(payload.email)
    if not identity: raise HTTPException(status_code=422,detail='Enter username or email')
    user=db.scalar(select(User).where(or_(User.username==identity,User.email==identity)))
    if not user or not verify_password(payload.password,user.password_hash): raise HTTPException(status_code=401,detail='Incorrect username/email or password')
    if user.account_status!='APPROVED': raise HTTPException(status_code=403,detail=f'Account status is {user.account_status}. Ask an Admin to approve it.')
    return {'access_token':create_token(user),'token_type':'bearer','user_id':user.user_id,'role':user.role}

@app.get('/auth/me')
def me(user:User=Depends(get_current_user)):
    return {'user_id':user.user_id,'username':user.username,'email':user.email,'full_name':user.full_name,'role':user.role,'account_status':user.account_status,'created_at':user.created_at}

@app.get('/admin/users/pending')
def pending_users(db:Session=Depends(get_db),admin:User=Depends(require_roles('ADMIN'))):
    rows=db.scalars(select(User).where(User.account_status=='PENDING').order_by(User.created_at)).all()
    return {'items':[{'user_id':u.user_id,'username':u.username,'email':u.email,'full_name':u.full_name,'role':u.role,'account_status':u.account_status,'created_at':u.created_at} for u in rows]}

@app.patch('/admin/users/{user_id}/status')
def update_user_status(user_id:int,payload:StatusUpdate,db:Session=Depends(get_db),admin:User=Depends(require_roles('ADMIN'))):
    target=db.get(User,user_id)
    if not target: raise HTTPException(status_code=404,detail='User not found')
    if target.user_id==admin.user_id and payload.status!='APPROVED': raise HTTPException(status_code=400,detail='You cannot suspend or reject your own Admin account')
    target.account_status=payload.status
    if payload.status=='APPROVED': target.approved_by=admin.user_id; target.approved_at=datetime.now()
    if payload.status in {'REJECTED','SUSPENDED'}: target.approved_by=admin.user_id; target.approved_at=datetime.now()
    db.add(Notification(user_id=target.user_id,title='Account status updated',message=f'Your account was marked {payload.status.lower()}.',notification_type='ACCOUNT'))
    db.commit()
    return {'message':f'Account marked {payload.status}','user_id':target.user_id,'account_status':target.account_status}

@app.get('/profile')
def get_profile(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    setting=db.get(ProfileSetting,user.user_id)
    return {'user_id':user.user_id,'username':user.username,'email':user.email,'full_name':user.full_name,'role':user.role,'account_status':user.account_status,'hospital':setting.hospital if setting else None,'created_at':user.created_at}

@app.put('/profile')
def update_profile(payload:ProfileUpdate,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    conflict=db.scalar(select(User).where(User.email==str(payload.email),User.user_id!=user.user_id))
    if conflict: raise HTTPException(status_code=409,detail='That email address is already used by another account')
    user.full_name=payload.full_name; user.email=str(payload.email)
    setting=db.get(ProfileSetting,user.user_id)
    if not setting: setting=ProfileSetting(user_id=user.user_id,hospital=payload.hospital); db.add(setting)
    else: setting.hospital=payload.hospital
    db.commit(); db.refresh(user)
    return {'user_id':user.user_id,'username':user.username,'email':user.email,'full_name':user.full_name,'role':user.role,'account_status':user.account_status,'hospital':setting.hospital}

@app.get('/notifications')
def get_notifications(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    rows=db.scalars(select(Notification).where(Notification.user_id==user.user_id).order_by(Notification.created_at.desc()).limit(100)).all()
    return {'items':[{'notification_id':n.notification_id,'patient_id':n.patient_id,'title':n.title,'message':n.message,'notification_type':n.notification_type,'is_read':bool(n.is_read),'created_at':n.created_at} for n in rows]}
@app.patch('/notifications/{notification_id}/read')
def mark_notification_read(notification_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    n=db.get(Notification,notification_id)
    if not n or n.user_id!=user.user_id: raise HTTPException(status_code=404,detail='Notification not found')
    n.is_read=True; db.commit(); return {'message':'Notification marked read'}

@app.post('/predict',response_model=PredictionResponse)
def predict_patient(request:PatientRequest):
    # Keep old trained pipeline available, but importing a missing model must not prevent app startup.
    try:
        from backend.agents.orchestrator import run_ckd_pipeline
    except Exception as exc: raise HTTPException(status_code=503,detail='Prediction model or agent dependencies are not ready. Ensure models/trained/ckd_model.joblib exists.') from exc
    result=run_ckd_pipeline(request.baseline_data.model_dump(),[v.model_dump() for v in request.visits])
    if 'error' in result: raise HTTPException(status_code=400,detail=result.get('details','Prediction failed'))
    if result.get('status') == 'validation_failed': raise HTTPException(status_code=422,detail=result.get('validation_issues') or 'Patient visit data failed validation')
    return result

# Analysis endpoint is registered by backend.patients so it shares one implementation.
