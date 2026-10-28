import re, uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.auth import require_roles
from backend.config import settings
from backend.database import get_db
from backend.models import KnowledgeResource, User

router=APIRouter(tags=['Knowledge resources'])
ALLOWED={'.pdf':'application/pdf','.txt':'text/plain'}

def resource_out(r): return {'resource_id':r.resource_id,'title':r.title,'category':r.category,'source_name':r.source_name,'source_url':r.source_url,'version_label':r.version_label,'original_filename':r.original_filename,'mime_type':r.mime_type,'file_size_bytes':r.file_size_bytes,'status':r.status,'created_at':r.created_at}

@router.get('/resources')
def list_resources(db:Session=Depends(get_db),user:User=Depends(require_roles('ADMIN','DOCTOR'))):
    items=db.scalars(select(KnowledgeResource).order_by(KnowledgeResource.created_at.desc())).all()
    return {'items':[resource_out(x) for x in items]}

@router.post('/resources',status_code=201)
async def add_resource(title:str=Form(...),category:str=Form(...),file:UploadFile=File(...),source_name:str|None=Form(None),source_url:str|None=Form(None),version_label:str|None=Form(None),db:Session=Depends(get_db),user:User=Depends(require_roles('ADMIN','DOCTOR'))):
    if not title.strip() or len(title)>255: raise HTTPException(status_code=422,detail='Title is required and must be at most 255 characters')
    suffix=Path(file.filename or '').suffix.lower()
    expected=ALLOWED.get(suffix)
    if not expected or file.content_type not in {expected,'application/octet-stream'}: raise HTTPException(status_code=415,detail='Only PDF and TXT files are accepted')
    max_bytes=settings.MAX_RESOURCE_MB*1024*1024
    content=await file.read(max_bytes+1)
    if len(content)>max_bytes: raise HTTPException(status_code=413,detail=f'File exceeds {settings.MAX_RESOURCE_MB} MB limit')
    if not content: raise HTTPException(status_code=422,detail='The uploaded file is empty')
    original=Path(file.filename or f'resource{suffix}').name[:255]
    stored=f'{uuid.uuid4().hex}{suffix}'
    root=Path(settings.RESOURCE_DIR).resolve(); root.mkdir(parents=True,exist_ok=True); final=(root/stored).resolve()
    if root not in final.parents: raise HTTPException(status_code=400,detail='Invalid file path')
    final.write_bytes(content)
    r=KnowledgeResource(title=title.strip(),category=category.strip()[:80],source_name=(source_name or None),source_url=(source_url or None),version_label=(version_label or None),original_filename=original,stored_filename=stored,mime_type=expected,file_size_bytes=len(content),uploaded_by=user.user_id,status='UPLOADED')
    db.add(r)
    try: db.commit(); db.refresh(r)
    except Exception as exc:
        db.rollback(); final.unlink(missing_ok=True); raise HTTPException(status_code=500,detail='Could not save resource metadata to MySQL') from exc
    return resource_out(r)
