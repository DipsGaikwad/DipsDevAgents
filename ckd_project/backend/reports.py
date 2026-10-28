from datetime import datetime, date, timedelta
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from backend.auth import require_roles
from backend.database import get_db
from backend.models import Patient, Visit, ProgressionLabel, User
from backend.patients import patient_query, patient_to_dict

router=APIRouter(tags=['Reports'])
NAVY=colors.HexColor('#163a5f'); BLUE=colors.HexColor('#317bb5'); PALE=colors.HexColor('#edf4fa'); GREY=colors.HexColor('#687b90')
def parse_pdf_filters(risk,source_code,search,period):
    since=None
    today=date.today()
    if period=='Last month': since=today-timedelta(days=30)
    elif period=='3 months': since=today-timedelta(days=90)
    elif period=='6 months': since=today-timedelta(days=183)
    elif period=='12 months': since=today-timedelta(days=365)
    elif period in (None,'','All'): pass
    else: raise HTTPException(status_code=422,detail='Unsupported period filter')
    return since

def current_lab(p):
    visits=sorted([v for v in p.visits if v.visit_date],key=lambda x:x.visit_date,reverse=True)
    for v in visits:
        if v.lab_results: return v.lab_results[0],v.visit_date
    return None,None

def pdf_header_footer(canvas,doc):
    canvas.saveState(); w,h=doc.pagesize
    canvas.setFillColor(NAVY); canvas.rect(0,h-12*mm,w,12*mm,stroke=0,fill=1)
    canvas.setFillColor(colors.white); canvas.setFont('Helvetica-Bold',9); canvas.drawString(15*mm,h-7.4*mm,'CKD CARE  |  CLINICAL DECISION SUPPORT')
    canvas.setFillColor(GREY); canvas.setFont('Helvetica',7); canvas.drawString(15*mm,8*mm,'Academic prototype · Verify all information with the treating clinician')
    canvas.drawRightString(w-15*mm,8*mm,f'Page {doc.page}'); canvas.restoreState()

def build_pdf(title,subtitle,patients,filters,patient_mode=False):
    buffer=BytesIO(); page=landscape(A4) if not patient_mode else A4
    doc=SimpleDocTemplate(buffer,pagesize=page,rightMargin=14*mm,leftMargin=14*mm,topMargin=18*mm,bottomMargin=16*mm,title=title,author='CKD Care')
    styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name='KTitle',parent=styles['Title'],textColor=NAVY,fontName='Helvetica-Bold',fontSize=20,leading=24,alignment=0,spaceAfter=4)); styles.add(ParagraphStyle(name='Sub',parent=styles['Normal'],textColor=GREY,fontSize=9,leading=13,spaceAfter=9)); styles.add(ParagraphStyle(name='Section',parent=styles['Heading2'],textColor=NAVY,fontSize=12,leading=15,spaceBefore=10,spaceAfter=6)); styles.add(ParagraphStyle(name='Tiny',parent=styles['Normal'],fontSize=7,leading=9,textColor=GREY)); styles.add(ParagraphStyle(name='Cell',parent=styles['Normal'],fontSize=7,leading=9))
    story=[Spacer(1,3*mm),Paragraph(title,styles['KTitle']),Paragraph(subtitle,styles['Sub']),Paragraph(f'Generated: {datetime.now().astimezone().strftime("%d %b %Y, %H:%M %Z")} &nbsp;&nbsp;|&nbsp;&nbsp; Patients included: {len(patients)}',styles['Sub']),Paragraph('Applied filters: '+(filters or 'None'),styles['Tiny']),Spacer(1,4*mm)]
    allrows=[]; egfr_points=[]; riskcounts={'High':0,'Medium':0,'Low':0,'Unassessed':0}; ages=[]; acrs=[]
    for p in patients:
        labs,latest_date=current_lab(p); egfr=(labs.egfr_ml_min_1_73m2 if labs else p.baseline_egfr); acr=(labs.acr_mg_g if labs else None); risk='Unassessed'
        label=p.progression_label if hasattr(p,'progression_label') else None
        # Use label-based rapid progression as a stored label, not as a validated current-risk probability.
        if label: risk='High' if label.rapid_progression else 'Low'
        riskcounts[risk]+=1
        if p.age_at_baseline is not None: ages.append(float(p.age_at_baseline))
        if acr is not None: acrs.append(float(acr))
        allrows.append([p.patient_id,p.full_name or '—',str(p.age_at_baseline or '—'),str(latest_date or '—'),str(egfr if egfr is not None else '—'),str(acr if acr is not None else '—'),risk])
        for v in p.visits:
            for l in v.lab_results:
                if l.egfr_ml_min_1_73m2 is not None and v.visit_date: egfr_points.append((v.visit_date,float(l.egfr_ml_min_1_73m2),p.patient_id))
    if not patient_mode:
        story.append(Paragraph('Cohort summary',styles['Section']))
        mean_egfr=[]
        for row in allrows:
            try: mean_egfr.append(float(row[4]))
            except: pass
        facts=[['Cohort size',len(patients)],['Mean latest eGFR',f'{sum(mean_egfr)/len(mean_egfr):.1f}' if mean_egfr else 'N/A'],['Mean baseline age',f'{sum(ages)/len(ages):.1f}' if ages else 'N/A'],['Patients with latest ACR',len(acrs)]]
        ft=Table(facts,colWidths=[45*mm,38*mm,45*mm,38*mm]); ft.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('TEXTCOLOR',(0,0),(-1,-1),NAVY),('FONTNAME',(0,0),(-1,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),('GRID',(0,0),(-1,-1),.35,colors.white),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)])); story.append(ft)
        story.append(Paragraph('Progression labels (stored labels, not new model predictions)',styles['Section']))
        rt=Table([['Category','Count','Share']]+[[k,v,f'{(v/len(patients)*100 if patients else 0):.1f}%'] for k,v in riskcounts.items()],colWidths=[50*mm,25*mm,30*mm]); rt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#dbe5ef')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('FONTSIZE',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)])); story.append(rt)
    else:
        p=patients[0]; labs,datev=current_lab(p)
        story.append(Paragraph('Patient summary',styles['Section']))
        patient_data=[['Field','Value','Field','Value'],['Patient ID',p.patient_id,'Display name',p.full_name or '—'],['Data source',p.source_code,'Source record',p.source_patient_id],['Age at baseline',p.age_at_baseline if p.age_at_baseline is not None else '—','Gender code',p.gender if p.gender is not None else '—'],['Latest visit',datev or '—','Latest eGFR',labs.egfr_ml_min_1_73m2 if labs else (p.baseline_egfr if p.baseline_egfr is not None else '—')],['Latest ACR',labs.acr_mg_g if labs else '—','Creatinine',labs.creatinine_mg_dl if labs else '—'],['Diabetes',str(p.diabetes),'Hypertension',str(p.hypertension)],['CVD',str(p.cvd),'IHD',str(p.ihd)]]
        t=Table(patient_data,colWidths=[32*mm,42*mm,32*mm,42*mm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('BACKGROUND',(0,1),(0,-1),PALE),('BACKGROUND',(2,1),(2,-1),PALE),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,1),(2,-1),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#dbe5ef')),('FONTSIZE',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)])); story.append(t)
    chartpts=sorted(egfr_points,key=lambda x:x[0])
    if patient_mode: chartpts=[x for x in chartpts if x[2]==patients[0].patient_id]
    if chartpts:
        story.append(Paragraph('Longitudinal eGFR trend',styles['Section']))
        fig,ax=plt.subplots(figsize=(7.6,2.3) if not patient_mode else (6.2,2.4)); dates=[x[0] for x in chartpts]; values=[x[1] for x in chartpts]
        ax.plot(dates,values,marker='o',linewidth=1.8,markersize=3,color='#317bb5'); ax.set_ylabel('eGFR (mL/min/1.73 m²)',fontsize=8); ax.grid(True,alpha=.22); ax.tick_params(axis='both',labelsize=7); fig.tight_layout()
        img=BytesIO(); fig.savefig(img,format='png',dpi=130); plt.close(fig); img.seek(0); story.append(Image(img,width=(180*mm if not patient_mode else 160*mm),height=(55*mm if not patient_mode else 60*mm)))
    else: story.append(Paragraph('No dated eGFR results were available for a trend chart.',styles['Tiny']))
    story.append(Paragraph('Visit and laboratory history',styles['Section']))
    rows=[['Patient ID','Visit date','Visit #','eGFR','Creatinine','ACR','SBP','DBP','Hb','K','Source']]
    for p in patients:
        for v in sorted(p.visits,key=lambda x:(x.visit_date or date.min,x.visit_id)):
            for l in v.lab_results or [None]:
                if l is None: rows.append([p.patient_id,str(v.visit_date or '—'),str(v.visit_number),'—','—','—','—','—','—','—','—'])
                else: rows.append([p.patient_id,str(v.visit_date or '—'),str(v.visit_number),str(l.egfr_ml_min_1_73m2 or '—'),str(l.creatinine_mg_dl or '—'),str(l.acr_mg_g or '—'),str(l.sbp_mmhg or '—'),str(l.dbp_mmhg or '—'),str(l.hemoglobin_g_dl or '—'),str(l.potassium_mmol_l or '—'),str(l.data_source or '—')])
    colw=[23*mm,22*mm,13*mm,17*mm,20*mm,17*mm,14*mm,14*mm,13*mm,12*mm,20*mm]
    if patient_mode: colw=[21*mm,22*mm,12*mm,16*mm,18*mm,16*mm,13*mm,13*mm,12*mm,11*mm,17*mm]
    table=Table(rows,colWidths=colw,repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),6.6),('GRID',(0,0),(-1,-1),.25,colors.HexColor('#dbe5ef')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)])); story.append(table)
    story.append(Spacer(1,4*mm)); story.append(Paragraph('Report limitations: missing values are shown as unavailable; the report does not fill them in. Where progression labels appear, they are historical stored labels and must not be represented as a newly generated or clinically validated prediction. This report supports academic review and does not replace clinical judgement.',styles['Tiny']))
    doc.build(story,onFirstPage=pdf_header_footer,onLaterPages=pdf_header_footer); buffer.seek(0); return buffer

@router.get('/reports/cohort/pdf')
def cohort_pdf(risk:str='All',source_code:str='All',search:str='',period:str='12 months',db:Session=Depends(get_db),user:User=Depends(require_roles('ADMIN','DOCTOR'))):
    since=parse_pdf_filters(risk,source_code,search,period); q=select(Patient).options(selectinload(Patient.visits).selectinload(Visit.lab_results)).order_by(Patient.patient_id)
    if source_code!='All': q=q.where(Patient.source_code==source_code)
    if search: q=q.where(or_(Patient.patient_id.like(f'%{search}%'),Patient.full_name.like(f'%{search}%'),Patient.source_patient_id.like(f'%{search}%')))
    items=db.scalars(q).unique().all(); filtered=[]
    for p in items:
        label=db.scalar(select(ProgressionLabel).where(ProgressionLabel.patient_id==p.patient_id)); computed='Unassessed' if label is None else ('High' if label.rapid_progression else 'Low')
        if risk!='All' and computed.lower()!=risk.lower(): continue
        if since:
            if not any(v.visit_date and v.visit_date>=since for v in p.visits): continue
        # Attach label for PDF summariser without changing ORM state.
        p.progression_label=label
        filtered.append(p)
    summary=f'risk={risk}; source={source_code}; search={search or "(none)"}; period={period}'
    pdf=build_pdf('CKD Care — Cohort Clinical Report','Filtered cohort overview, longitudinal data and source metadata',filtered,summary,False)
    return StreamingResponse(pdf,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="ckd-cohort-report.pdf"'})

@router.get('/reports/patients/{patient_id}/pdf')
def patient_pdf(patient_id:str,db:Session=Depends(get_db),user:User=Depends(require_roles('ADMIN','DOCTOR'))):
    p=db.scalar(select(Patient).where(Patient.patient_id==patient_id).options(selectinload(Patient.visits).selectinload(Visit.lab_results)))
    if not p: raise HTTPException(status_code=404,detail='Patient not found')
    p.progression_label=db.scalar(select(ProgressionLabel).where(ProgressionLabel.patient_id==patient_id))
    pdf=build_pdf(f'CKD Care — Patient Report {patient_id}','Patient-specific clinical summary and dated laboratory history',[p],'single patient',True)
    return StreamingResponse(pdf,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="ckd-{patient_id}-report.pdf"'})
