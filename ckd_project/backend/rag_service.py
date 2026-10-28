"""Local retrieval pipeline for the CKD Care approved-reference library."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from backend.config import settings
CHUNK_SIZE=1100
CHUNK_OVERLAP=180
TOP_K=5
COLLECTION_NAME="ckd_clinical_knowledge"
_client=None
_model=None

def _get_client():
    global _client
    if _client is None:
        path=Path(settings.RAG_CHROMA_DIR); path.mkdir(parents=True,exist_ok=True)
        _client=chromadb.PersistentClient(path=str(path))
    return _client

def _get_model():
    global _model
    if _model is None:
        _model=SentenceTransformer(settings.RAG_EMBEDDING_MODEL,cache_folder=settings.RAG_MODEL_CACHE)
    return _model

def _collection():
    return _get_client().get_or_create_collection(name=COLLECTION_NAME,metadata={"hnsw:space":"cosine"})

def extract_text(path:Path)->str:
    if path.suffix.lower()==".txt": return path.read_text(encoding="utf-8",errors="replace")
    if path.suffix.lower()==".pdf":
        reader=PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError("Unsupported document type; use PDF or TXT")

def chunk_text(text:str)->list[str]:
    text=re.sub(r"[ \t]+"," ",text); text=re.sub(r"\n{3,}","\n\n",text).strip()
    chunks=[]; start=0
    while start<len(text):
        end=min(start+CHUNK_SIZE,len(text))
        if end<len(text):
            boundary=max(text.rfind("\n",start+CHUNK_SIZE//2,end),text.rfind(". ",start+CHUNK_SIZE//2,end))
            if boundary>start: end=boundary+1
        part=text[start:end].strip()
        if part: chunks.append(part)
        if end>=len(text): break
        start=max(end-CHUNK_OVERLAP,start+1)
    return chunks

def index_resource(resource:Any,file_path:Path)->int:
    chunks=chunk_text(extract_text(file_path))
    if not chunks: raise ValueError("No extractable text found. Scanned/image-only PDFs need OCR before indexing.")
    coll=_collection(); old=coll.get(where={"resource_id":int(resource.resource_id)},include=["metadatas"])
    if old.get("ids"): coll.delete(ids=old["ids"])
    vectors=_get_model().encode(chunks,normalize_embeddings=True).tolist()
    ids=[f"resource-{resource.resource_id}-{i}" for i in range(len(chunks))]
    metas=[{"resource_id":int(resource.resource_id),"title":str(resource.title)[:500],"category":str(resource.category)[:100],"source_name":str(resource.source_name or "Unknown")[:300],"source_url":str(resource.source_url or "")[:1000],"version_label":str(resource.version_label or "")[:150],"filename":str(resource.original_filename)[:255],"chunk_index":i} for i in range(len(chunks))]
    for i in range(0,len(chunks),64): coll.add(ids=ids[i:i+64],documents=chunks[i:i+64],embeddings=vectors[i:i+64],metadatas=metas[i:i+64])
    return len(chunks)

def retrieve(question:str,top_k:int=TOP_K)->list[dict[str,Any]]:
    coll=_collection()
    if coll.count()==0: return []
    vector=_get_model().encode([question],normalize_embeddings=True).tolist()
    result=coll.query(query_embeddings=vector,n_results=min(max(top_k,1),coll.count()),include=["documents","metadatas","distances"])
    output=[]
    docs=(result.get("documents") or [[]])[0]; metas=(result.get("metadatas") or [[]])[0]; distances=(result.get("distances") or [[]])[0]
    for i,doc in enumerate(docs):
        meta=metas[i] or {}; distance=distances[i]
        output.append({"text":doc,"title":meta.get("title","Untitled source"),"category":meta.get("category",""),"source_name":meta.get("source_name",""),"source_url":meta.get("source_url",""),"version_label":meta.get("version_label",""),"filename":meta.get("filename",""),"chunk_index":meta.get("chunk_index",0),"score":round(max(0.,1.-float(distance)),3) if distance is not None else None})
    return output

def answer_question(question:str,top_k:int=TOP_K)->dict[str,Any]:
    passages=retrieve(question,top_k)
    if not passages:
        return {"answer":"I cannot answer from the approved knowledge base yet because no documents have been indexed. Upload a readable clinical reference in Knowledge Base, then index it.","sources":[],"grounded":False}
    selected=[p for p in passages if p["score"] is None or p["score"]>=settings.RAG_MIN_RELEVANCE]
    source_keys=("title","category","source_name","source_url","version_label","filename","score")
    if not selected:
        return {"answer":"I could not find sufficiently relevant material in the approved knowledge base. Try a more specific question or add a suitable guideline.","sources":[{k:p[k] for k in source_keys} for p in passages[:3]],"grounded":False}
    excerpts=[]
    for i,p in enumerate(selected[:3],1):
        excerpt=p["text"].strip()
        if len(excerpt)>650: excerpt=excerpt[:650].rsplit(" ",1)[0]+"…"
        excerpts.append(f"Source {i}: {p['title']}\n{excerpt}")
    answer="Relevant passages retrieved from the indexed clinical references are shown below. Verify the cited source and its current version before using it in clinical review.\n\n"+"\n\n".join(excerpts)
    sources=[]; seen=set()
    for p in selected:
        key=(p["title"],p["source_url"],p["filename"])
        if key in seen: continue
        seen.add(key); sources.append({k:p[k] for k in source_keys})
    return {"answer":answer,"sources":sources[:5],"grounded":True}

def index_status()->dict[str,Any]:
    try:
        c=_collection(); return {"available":True,"indexed_chunks":c.count(),"collection":COLLECTION_NAME}
    except Exception as exc:
        return {"available":False,"indexed_chunks":0,"collection":COLLECTION_NAME,"error":str(exc)}
