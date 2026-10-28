from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.auth import require_roles
from backend.config import settings
from backend.database import get_db
from backend.models import KnowledgeResource,User
from backend.rag_service import answer_question,index_resource,index_status
router=APIRouter(prefix="/clinical-assistant",tags=["Clinical assistant / RAG"])
class ChatRequest(BaseModel):
    question:str=Field(min_length=2,max_length=2000)
    patient_id:str|None=Field(default=None,max_length=20)
@router.get("/status")
def assistant_status(user:User=Depends(require_roles("ADMIN","DOCTOR"))): return index_status()
@router.post("/chat")
def chat(payload:ChatRequest,user:User=Depends(require_roles("ADMIN","DOCTOR"))):
    question=payload.question.strip()
    if len(question)<2: raise HTTPException(status_code=422,detail="Enter a clinical knowledge question")
    result=answer_question(question)
    return {"question":question,"answer":result["answer"],"sources":result["sources"],"grounded":result["grounded"],"notice":"Educational prototype only. This response is not a diagnosis or treatment recommendation and is not a substitute for clinician judgement."}
@router.post("/index/{resource_id}")
def index_one(resource_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles("ADMIN","DOCTOR"))):
    resource=db.get(KnowledgeResource,resource_id)
    if not resource: raise HTTPException(status_code=404,detail="Knowledge resource not found")
    root=Path(settings.RESOURCE_DIR).resolve(); path=(root/resource.stored_filename).resolve()
    if root not in path.parents or not path.is_file():
        resource.status="FAILED"; db.commit(); raise HTTPException(status_code=404,detail="Stored resource file is missing")
    resource.status="PROCESSING"; db.commit()
    try:
        count=index_resource(resource,path); resource.status="INDEXED"; db.commit()
        return {"message":"Resource indexed successfully","resource_id":resource_id,"chunks_indexed":count,"status":resource.status}
    except Exception as exc:
        db.rollback(); failed=db.get(KnowledgeResource,resource_id)
        if failed: failed.status="FAILED"; db.commit()
        raise HTTPException(status_code=422,detail=f"Could not index resource: {str(exc)[:400]}") from exc
@router.post("/reindex-all")
def reindex_all(db:Session=Depends(get_db),user:User=Depends(require_roles("ADMIN","DOCTOR"))):
    rows=db.scalars(select(KnowledgeResource).where(KnowledgeResource.status.in_(["UPLOADED","FAILED","INDEXED"]))).all(); output=[]
    for r in rows:
        root=Path(settings.RESOURCE_DIR).resolve(); path=(root/r.stored_filename).resolve()
        try:
            if root not in path.parents or not path.is_file(): raise FileNotFoundError("Stored resource file is missing")
            r.status="PROCESSING"; db.commit(); count=index_resource(r,path); r.status="INDEXED"; db.commit()
            output.append({"resource_id":r.resource_id,"title":r.title,"status":"INDEXED","chunks_indexed":count})
        except Exception as exc:
            db.rollback(); current=db.get(KnowledgeResource,r.resource_id)
            if current: current.status="FAILED"; db.commit()
            output.append({"resource_id":r.resource_id,"title":r.title,"status":"FAILED","error":str(exc)[:250]})
    return {"items":output,"total":len(output),"indexed":sum(x["status"]=="INDEXED" for x in output)}
