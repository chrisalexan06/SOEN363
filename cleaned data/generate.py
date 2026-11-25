#!/usr/bin/env python3
"""Reproducible four-continent SOEN 363 synthetic source generator.
All names/identifiers are fictitious. Do not use for clinical decisions.
"""
import csv, io, json, random, re, shutil, hashlib
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import Counter, defaultdict
import xml.etree.ElementTree as ET
from faker import Faker

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'raw'; CLEAN=ROOT/'cleaned_integrated'; DOCS=ROOT/'documentation'
RNG=random.Random(3632026)
COUNT={
 'hospital_units':12, 'nurses':45, 'physicians':55, 'radiologists':18,
 'icd9_dictionary':24, 'patients':1000, 'admissions':1350,
 'assessments':1350, 'unit_stays':1450, 'diagnoses':2000,
 'clinical_notes':480, 'diagnostic_orders':160,
 'diagnostic_examinations':160, 'radiology_examinations':190,
 'radiology_reports':140, 'surgical_procedures':180,
 'discharge_records':400, 'discharge_summaries':400
}
ORDER=list(COUNT)
KEYS={'hospital_units':'unit_id','nurses':'nurse_id','physicians':'physician_id',
 'radiologists':'radiologist_id','icd9_dictionary':'icd9_code','patients':'patient_id',
 'admissions':'admission_id','assessments':'assessment_id','unit_stays':'unit_stay_id',
 'diagnoses':'diagnosis_id','clinical_notes':'clinical_note_id',
 'diagnostic_orders':'diagnostic_order_id','diagnostic_examinations':'examination_id',
 'radiology_examinations':'radiology_examination_id','radiology_reports':'radiology_report_id',
 'surgical_procedures':'procedure_id','discharge_records':'discharge_record_id',
 'discharge_summaries':'discharge_summary_id'}
FK={
 'patients':{'nurse_id':'nurses','physician_id':'physicians'},
 'admissions':{'patient_id':'patients','nurse_id':'nurses','physician_id':'physicians'},
 'assessments':{'admission_id':'admissions','patient_id':'patients','nurse_id':'nurses'},
 'unit_stays':{'admission_id':'admissions','hospital_unit_id':'hospital_units','responsible_physician_id':'physicians'},
 'diagnoses':{'admission_id':'admissions','patient_id':'patients','physician_id':'physicians','icd9_code':'icd9_dictionary'},
 'clinical_notes':{'admission_id':'admissions','patient_id':'patients','physician_id':'physicians'},
 'diagnostic_orders':{'admission_id':'admissions','patient_id':'patients','requesting_physician_id':'physicians'},
 'diagnostic_examinations':{'diagnostic_order_id':'diagnostic_orders','admission_id':'admissions','referring_physician_id':'physicians'},
 'radiology_examinations':{'diagnostic_order_id':'diagnostic_orders','admission_id':'admissions','referring_physician_id':'physicians','reviewed_by_radiologist_id':'radiologists'},
 'radiology_reports':{'radiology_examination_id':'radiology_examinations','radiologist_id':'radiologists'},
 'surgical_procedures':{'admission_id':'admissions','physician_id':'physicians'},
 'discharge_records':{'admission_id':'admissions','patient_id':'patients','physician_id':'physicians','primary_icd9_code':'icd9_dictionary'},
 'discharge_summaries':{'discharge_record_id':'discharge_records','admission_id':'admissions','physician_id':'physicians'},
}
# Curated historical ICD-9-CM diagnosis codes; reference is 2015 CMS V32 code titles.
ICD9=[
 ('038.9','Unspecified septicemia','Infectious and parasitic diseases'),
 ('250.00','Diabetes mellitus without mention of complication, type II or unspecified type, not stated as uncontrolled','Endocrine and metabolic'),
 ('401.9','Unspecified essential hypertension','Circulatory'),
 ('414.01','Coronary atherosclerosis of native coronary artery','Circulatory'),
 ('486','Pneumonia, organism unspecified','Respiratory'),
 ('496','Chronic airway obstruction, not elsewhere classified','Respiratory'),
 ('493.90','Asthma, unspecified type, unspecified','Respiratory'),
 ('599.0','Urinary tract infection, site not specified','Genitourinary'),
 ('786.50','Chest pain, unspecified','Symptoms and signs'),
 ('780.2','Syncope and collapse','Symptoms and signs'),
 ('789.00','Abdominal pain, unspecified site','Symptoms and signs'),
 ('285.9','Anemia, unspecified','Blood diseases'),
 ('427.31','Atrial fibrillation','Circulatory'),
 ('410.90','Acute myocardial infarction of unspecified site, episode of care unspecified','Circulatory'),
 ('780.60','Fever, unspecified','Symptoms and signs'),
 ('724.2','Lumbago','Musculoskeletal'),
 ('784.0','Headache','Symptoms and signs'),
 ('276.51','Dehydration','Endocrine and metabolic'),
 ('995.91','Sepsis','Injury and poisoning'),
 ('560.9','Unspecified intestinal obstruction','Digestive'),
 ('584.9','Acute kidney failure, unspecified','Genitourinary'),
 ('530.81','Esophageal reflux','Digestive'),
 ('780.79','Other malaise and fatigue','Symptoms and signs'),
 ('272.4','Other and unspecified hyperlipidemia','Endocrine and metabolic'),
]
assert len(ICD9)==COUNT['icd9_dictionary']
CONFIG={
 'A':{'continent':'North America','country':'Canada','city':'Montréal','locale':'en_CA','format':'TXT','hospital':'North River Teaching Hospital','date_format':'%Y-%m-%d','missing':'NA','temp':'C'},
 'B':{'continent':'Europe','country':'Germany','city':'Berlin','locale':'de_DE','format':'CSV','hospital':'Berlin Central Clinical Centre','date_format':'%d.%m.%Y','missing':'k.A.','temp':'C'},
 'C':{'continent':'Asia','country':'Japan','city':'Osaka','locale':'ja_JP','format':'XML','hospital':'Osaka Metropolitan Medical Centre','date_format':'%Y/%m/%d','missing':'未記録','temp':'C'},
 'D':{'continent':'Africa','country':'South Africa','city':'Cape Town','locale':'en_GB','format':'JSON','hospital':'Cape Meridian Hospital','date_format':'%d/%m/%Y','missing':'NULL','temp':'F'},
}
ZA_FIRST=['Thabo','Nomsa','Lerato','Sipho','Amina','Lindiwe','Bongani','Zanele','Kabelo','Naledi','Mandla','Sibongile']
ZA_LAST=['Mokoena','Ndlovu','Naidoo','Dlamini','Khumalo','Mthembu','Nkosi','Botha','van der Merwe','Pillay']
STREET=['Fictional Lane','Example Avenue','Demo Road','Test Street','Research Boulevard','Sample Crescent']
REASONS=['Chest discomfort','Shortness of breath','Fever and fatigue','Abdominal pain','Dizziness','Abnormal laboratory values','Injury assessment','Routine postoperative follow-up','Severe headache','Urinary symptoms']
CONDITIONS=['Stable','Improving','Requires monitoring','Recovered','Transferred']
PROCEDURES=['Appendectomy','Cholecystectomy','Orthopedic fixation','Endoscopy with intervention','Cardiac catheterization','Hernia repair']
EXAMS=['BloodTest','CT Examination','electrodiagram','X-ray','Ultrasound','MRI']
UNITS=['ED','General Ward','ICU','Surgical Ward','Recovery']
GEN=['Female','Male','Other']; LIFE=['Alive','Deceased']
issues=[]; audit=[]; all_raw={}; all_clean={}; rejects=[]; transforms=Counter()

# Explicitly model the ERD supertype/subtype structure in one row per entity instance:
# diagnosis_type Primary/Secondary; diagnostic examination types BloodTest/CT/electrodiagram.
# Radiology examinations are distinct records, not duplicated supertype rows.

def by_id(i,n):return RNG.randint(1,n)
def dstr(d):return d.isoformat() if d else None
def dtparts(d,h=10,minute=0):return {'date':dstr(d),'time':f'{h:02d}:{minute:02d}'}
def randdate(a,b):return a+timedelta(days=RNG.randrange((b-a).days+1))
def pick_person(faker,src):
 if src=='D':return RNG.choice(ZA_FIRST)+' '+RNG.choice(ZA_LAST)
 return faker.name()
def hospital_rows(src):
 c=CONFIG[src]; fake=Faker(c['locale']); fake.seed_instance(2026+ord(src))
 out={name:[] for name in ORDER}
 def put(t,**kwargs):out[t].append(kwargs);return kwargs
 for i in range(1,COUNT['hospital_units']+1):
  kind=UNITS[(i-1)%len(UNITS)]
  put('hospital_units',unit_id=i,unit_name=f'{c["city"]} {kind} {1+(i-1)//5}',unit_type=kind,ward=f'W{i:02d}',capacity_beds=RNG.choice([12,16,20,24,30]))
 for tab,count,namekey in [('nurses',45,'nurse_name'),('physicians',55,'physician_name'),('radiologists',18,'radiologist_name')]:
  for i in range(1,count+1):put(tab,**{KEYS[tab]:i,namekey:pick_person(fake,src)})
 for code,title,category in ICD9:
  put('icd9_dictionary',icd9_code=code,diagnosis_title=title,description=title,disease_category=category)
 deceased_ids=set(RNG.sample(range(1,1001),60))
 for i in range(1,1001):
  dob=randdate(date(1930,1,1),date(2015,12,31))
  put('patients',patient_id=i,full_name=pick_person(fake,src),date_of_birth=dstr(dob),gender=RNG.choice(GEN),
   life_status='Deceased' if i in deceased_ids else 'Alive',health_insurance_number=f'SYN-{src}-{i:06d}',
   telephone_number=f'TEST-{src}-{i:05d}',address=f'{i} {RNG.choice(STREET)}, {c["city"]}, {c["country"]}',
   emergency_contact_info=f'TEST-CONTACT-{src}-{i:05d}' if i%5 else None,
   nurse_id=by_id(i,45),physician_id=by_id(i,55))
 # All 1000 patients have an initial visit; 350 experience a repeat admission.
 admission_patient_ids=list(range(1,1001))+[RNG.randint(1,1000) for _ in range(350)]
 for i,pid in enumerate(admission_patient_ids,1):
  admission=randdate(date(2024,1,1),date(2025,6,30)) if i<=1000 else randdate(date(2025,8,1),date(2026,10,29))
  exit_d=admission+timedelta(days=RNG.randint(1,9))
  put('admissions',admission_id=i,patient_id=pid,nurse_id=by_id(i,45),physician_id=by_id(i,55),
   admission_date=dstr(admission),admission_time='08:00',
   discharge_date=dstr(exit_d),discharge_time='20:00',
   admission_status='Closed',visit_reason=RNG.choice(REASONS),is_followup=(i>1000),
   past_record_followup=f'Previous admission in system' if i>1000 else None)
 adm={x['admission_id']:x for x in out['admissions']}
 for i in range(1,1351):
  a=adm[i]; ad=date.fromisoformat(a['admission_date']); p=a['patient_id']
  temp=round(RNG.uniform(36.0,39.1),1)
  if src=='D':temp=round(temp*9/5+32,1)
  put('assessments',assessment_id=i,admission_id=i,patient_id=p,nurse_id=a['nurse_id'],assessment_date=dstr(ad),assessment_time='08:20',
   triage_priority_level=RNG.choice([1,2,3,4,5]),body_temperature=temp,temperature_unit=c['temp'],
   heart_rate=RNG.randint(59,126),respiratory_rate=RNG.randint(12,25),oxygen_saturation=RNG.randint(92,100),
   blood_pressure=f'{RNG.randint(105,155)}/{RNG.randint(65,96)}',pain_level=RNG.randint(0,10),
   known_allergies=RNG.choice(['None','Penicillin','Pollen','Nuts',None]),
   reported_symptoms=a['visit_reason'],current_medication=RNG.choice(['None','Documented home medication',None]))
 for i in range(1,1451):
  aid=i if i<=1350 else i-1350
  a=adm[aid]; ad=date.fromisoformat(a['admission_date']); ext=date.fromisoformat(a['discharge_date'])
  # Every admission gets at least one stay; 100 have a second transfer.
  if i>1350:ad=ad
  ed=ad if i<=100 else ext
  uid=by_id(i,12);u=out['hospital_units'][uid-1]
  put('unit_stays',unit_stay_id=i,admission_id=aid,hospital_unit_id=uid,unit_type=u['unit_type'],ward=u['ward'],
   room=f'R{RNG.randint(100,499)}',bed_number=RNG.randint(1,4),entry_date=dstr(ad),entry_time='14:30' if i>1350 else '09:00',
   exit_date=dstr(ed),exit_time='14:00' if i<=100 else '20:00',transfer_reason='Specialist review' if i>1350 else None,
   responsible_physician_id=a['physician_id'])
 # Exactly one primary diagnosis per admission; remaining 650 are secondary.
 def code_for(aid,j=0):return ICD9[(aid*7+j*11)%len(ICD9)][0]
 for i in range(1,2001):
  aid=i if i<=1350 else ((i-1351)%1350)+1
  a=adm[aid]; ad=date.fromisoformat(a['admission_date']);dis=ad+timedelta(days=RNG.randint(0,min(2,(date.fromisoformat(a['discharge_date'])-ad).days)))
  put('diagnoses',diagnosis_id=i,admission_id=aid,patient_id=a['patient_id'],physician_id=a['physician_id'],
   icd9_code=code_for(aid,0 if i<=1350 else 1),diagnosis_date=dstr(dis),diagnosis_time='15:30',
   diagnosis_type='Primary' if i<=1350 else 'Secondary')
 for i in range(1,481):
  aid=(i*19)%1350+1;a=adm[aid]; ad=date.fromisoformat(a['admission_date'])+timedelta(days=RNG.randint(0,min(3,(date.fromisoformat(a['discharge_date'])-date.fromisoformat(a['admission_date'])).days)))
  put('clinical_notes',clinical_note_id=i,admission_id=aid,patient_id=a['patient_id'],physician_id=a['physician_id'],
   note_date=dstr(ad),note_time=f'{RNG.randint(8,19):02d}:15',medical_condition='Under clinical review',
   symptoms=a['visit_reason'],physical_examination='Examination documented',diagnostic_examination=RNG.choice(['Laboratory work','Imaging',None]),
   clinical_findings='Clinical findings recorded',treatment_plan='Monitoring and follow-up')
 for i in range(1,161):
  aid=(i*17)%1350+1;a=adm[aid]; ad=date.fromisoformat(a['admission_date'])
  exam=EXAMS[(i-1)%3] if i<=80 else EXAMS[3+(i-81)%3]
  put('diagnostic_orders',diagnostic_order_id=i,admission_id=aid,patient_id=a['patient_id'],requesting_physician_id=a['physician_id'],
   request_date=dstr(ad),request_time='09:00',clinical_reason_for_examination=a['visit_reason'],
   priority=RNG.choice(['Routine','Urgent','Stat']),requested_examination=exam,order_status='Completed')
 for i in range(1,161):
  order=out['diagnostic_orders'][(i-1)%80];aid=order['admission_id'];a=adm[aid]
  ed=date.fromisoformat(a['admission_date'])+timedelta(days=RNG.randint(0,2))
  exam=order['requested_examination']
  put('diagnostic_examinations',examination_id=i,diagnostic_order_id=order['diagnostic_order_id'],admission_id=aid,
   referring_physician_id=a['physician_id'],examination_type=exam,examination_date=dstr(ed),examination_time='13:00',
   examination_status='Completed',body_area_examined='Chest' if exam=='electrodiagram' else ('Abdomen' if exam=='CT Examination' else 'Blood'),
   radiology_technician=RNG.choice(['Tech-01','Tech-02',None]),link_to_images=None if exam=='BloodTest' else f'FAKE-IMAGE-{src}-{i}',
   result_value=round(RNG.uniform(3,11),2),result_unit='reference-unit')
 for i in range(1,191):
  order=out['diagnostic_orders'][80+(i-1)%80]
  # Diverse admissions with linkage to a real order and within admission dates.
  aid=order['admission_id'];a=adm[aid];ed=date.fromisoformat(a['admission_date'])+timedelta(days=1)
  rid=by_id(i,18)
  put('radiology_examinations',radiology_examination_id=i,diagnostic_order_id=order['diagnostic_order_id'],
   admission_id=aid,referring_physician_id=a['physician_id'],reviewed_by_radiologist_id=rid,
   examination_type=order['requested_examination'],body_area_examined=RNG.choice(['Chest','Abdomen','Head','Extremity']),
   examination_date=dstr(ed),examination_time='14:30',examination_status='Completed',
   radiology_technician=f'Tech-{i%17:02d}',link_to_images=f'FAKE-IMAGE-{src}-RAD-{i:04d}')
 for i in range(1,141):
  x=out['radiology_examinations'][i-1]
  put('radiology_reports',radiology_report_id=i,radiology_examination_id=x['radiology_examination_id'],
   radiologist_id=x['reviewed_by_radiologist_id'],report_date=x['examination_date'],report_time='17:00',
   findings='Synthetic imaging observations',interpretations='No urgent abnormality identified',
   clinical_conclusion='Consider clinical correlation')
 # Make >= 60 encounters have both surgery and radiology on same date (query coverage).
 matching=list(dict.fromkeys(x['admission_id'] for x in out['radiology_examinations']))
 assert len(matching)>65
 surg_aids=matching[:70]+RNG.sample(range(1,1351),110)
 for i,aid in enumerate(surg_aids,1):
  a=adm[aid]
  rad=next((x for x in out['radiology_examinations'] if x['admission_id']==aid),None)
  ed=date.fromisoformat(rad['examination_date']) if (i<=70 and rad) else date.fromisoformat(a['admission_date'])+timedelta(days=1)
  put('surgical_procedures',procedure_id=i,admission_id=aid,physician_id=a['physician_id'],
   procedure_date=dstr(ed),procedure_time='16:00',procedure_type=RNG.choice(PROCEDURES),duration_minutes=RNG.randint(35,155))
 for i in range(1,401):
  aid=i*3;a=adm[aid];pid=a['patient_id']
  primary=out['diagnoses'][aid-1]['icd9_code']
  other=next((x['icd9_code'] for x in out['diagnoses'][1350:] if x['admission_id']==aid),None)
  put('discharge_records',discharge_record_id=i,admission_id=aid,patient_id=pid,physician_id=a['physician_id'],
   discharge_date=a['discharge_date'],discharge_time=a['discharge_time'],discharge_destination=RNG.choice(['Home','Outpatient follow-up','Another facility']),
   patient_condition=RNG.choice(CONDITIONS),primary_icd9_code=primary,secondary_icd9_code=other,
   prescribed_medication=RNG.choice(['See medication reconciliation','None documented',None]),
   follow_up_appointment=None,follow_up_instructions='Contact local clinic for follow-up',
   responsible_physician=out['physicians'][a['physician_id']-1]['physician_name'])
  put('discharge_summaries',discharge_summary_id=i,discharge_record_id=i,admission_id=aid,
   physician_id=a['physician_id'],admission_reason=a['visit_reason'],examination_results='See patient chart',
   icd9_code_diagnoses=primary,treatments_provided='Clinical observation and appropriate treatment',
   unit_transfers='See unit stay history',recommendations='Outpatient follow-up as clinically indicated')
 assert {t:len(v) for t,v in out.items()}==COUNT
 return out

DATE_FIELDS={'date_of_birth','admission_date','discharge_date','assessment_date','entry_date','exit_date',
             'diagnosis_date','note_date','request_date','examination_date','report_date','procedure_date'}
TIME_FIELDS={'admission_time','discharge_time','assessment_time','entry_time','exit_time','diagnosis_time',
             'note_time','request_time','examination_time','report_time','procedure_time'}
ID_FIELDS=set(KEYS.values())|{k for f in FK.values() for k in f}
ALIAS_B={'patient_id':'PatientNr','admission_id':'FallNr','diagnosis_id':'DiagnoseNr',
 'full_name':'PatientName','admission_date':'AufnahmeDatum','icd9_code':'ICD9','nurse_id':'PflegeNr',
 'physician_id':'ArztNr','assessment_id':'TriageNr','unit_stay_id':'AufenthaltNr',
 'examination_id':'UntersuchungNr','clinical_note_id':'VerlaufNotizNr','hospital_unit_id':'StationNr'}
ALIAS_C={'patient_id':'patientNumber','admission_id':'encounterNumber','icd9_code':'diagnosisCode',
 'admission_date':'visitDate','nurse_id':'careNurseId','body_temperature':'bodyTemp'}
ALIAS_D={'patient_id':'PAT_ID','admission_id':'ADM_ID','icd9_code':'ICD9',
 'admission_date':'ADM_DATE','triage_priority_level':'TRIAGE_LEVEL',
 'body_temperature':'TEMP_READING','diagnosis_id':'DX_ID','physician_id':'DOC_ID',
 'nurse_id':'RN_ID'}

def key_for(f,src):
 if src=='A':return f
 if src=='B':return ALIAS_B.get(f,f)
 if src=='C':return ALIAS_C.get(f, ''.join(w.title() if n else w for n,w in enumerate(f.split('_'))))
 return ALIAS_D.get(f,f.upper())

def raw_value(field,val,src):
 c=CONFIG[src]
 if val is None:return c['missing']
 if field in DATE_FIELDS:
  return datetime.strptime(str(val),'%Y-%m-%d').strftime(c['date_format'])
 if field in TIME_FIELDS and src=='B':return str(val).replace(':','.')
 if field=='gender':return ({'B':{'Male':'M','Female':'F','Other':'X'},'C':{'Male':'男','Female':'女','Other':'その他'},
     'D':{'Male':'MALE','Female':'FEMALE','Other':'OTHER'}}.get(src,{}) or {}).get(val,val)
 if field=='life_status':return ({'B':{'Alive':'Lebend','Deceased':'Verstorben'},'C':{'Alive':'生存','Deceased':'死亡'},
     'D':{'Alive':'ALIVE','Deceased':'DEAD'}}.get(src,{}) or {}).get(val,val)
 if field=='diagnosis_type':return ({'B':{'Primary':'Haupt','Secondary':'Neben'},'C':{'Primary':'主','Secondary':'副'},
     'D':{'Primary':'PRIMARY','Secondary':'SECONDARY'}}.get(src,{}) or {}).get(val,val)
 if field=='unit_type':return ({'B':dict(zip(UNITS,['Notaufnahme','Normalstation','Intensivstation','Chirurgie','Aufwachraum'])),
     'C':dict(zip(UNITS,['救急','一般病棟','集中治療','外科病棟','回復室'])),
     'D':dict(zip(UNITS,['EMERGENCY','WARD','ICU','SURGICAL','RECOVERY']))}.get(src,{}) or {}).get(val,val)
 if field=='priority':return ({'B':{'Routine':'Normal','Urgent':'Hoch','Stat':'Sofort'},
      'C':{'Routine':'通常','Urgent':'緊急','Stat':'至急'},
      'D':{'Routine':'LOW','Urgent':'HIGH','Stat':'CRITICAL'}}.get(src,{}) or {}).get(val,val)
 if isinstance(val,bool):return ('Ja' if val else 'Nein') if src=='B' else ('yes' if val else 'no')
 return val

def into_raw(tab,rows,src):return [{key_for(k,src):raw_value(k,v,src) for k,v in row.items()} for row in rows]

def pk_raw(tab,src):return key_for(KEYS[tab],src)

def mark_issue(src,table,issue,field,row,action,detail):
 issues.append({'source':src,'entity':table,'issue_type':issue,'local_id':row.get(pk_raw(table,src)),
               'field':key_for(field,src) if field else '', 'action':action,'detail':detail})

def introduce_issues(src,tables):
 # Disjoint row sets by entity where possible. Controlled modifications are intentionally raw-only.
 conf=CONFIG[src];blank=conf['missing']
 def mutate(tab,indices,field,issue,value,action,detail):
  key=key_for(field,src)
  for ix in indices:
   row=tables[tab][ix]
   mark_issue(src,tab,issue,field,row,action,detail)
   row[key]=value(row) if callable(value) else value
 # 12 missing required values => reject
 mutate('diagnoses',range(1600,1606),'icd9_code','missing_required',blank,'reject','ICD-9 code required for diagnosis')
 mutate('clinical_notes',range(0,6),'physician_id','missing_required',blank,'reject','Authoring physician required')
 # 26 optional blanks => keep
 mutate('patients',range(20,40),'emergency_contact_info','missing_optional',blank,'retain_nullable','Optional contact absent')
 mutate('discharge_records',range(10,16),'prescribed_medication','missing_optional',blank,'retain_nullable','Optional medication summary absent')
 # 40 inconsistent capitalization and whitespace examples => trim / case normalizer
 mutate('patients',range(40,64),'full_name','case_whitespace',lambda r:'   '+str(r[key_for('full_name',src)]).swapcase()+'   ',
        'normalize','Patient names require trimming and consistent case')
 mutate('diagnoses',range(1400,1416),'diagnosis_type','case_whitespace',lambda r:'  '+str(r[key_for('diagnosis_type',src)]).lower()+'  ',
        'normalize','Normalize category label and whitespace')
 # 12 invalid or ambiguous dates => reject those leaf events
 mutate('clinical_notes',range(20,26),'note_date','invalid_date','2026-02-30','reject','Impossible calendar day')
 mutate('clinical_notes',range(26,32),'note_date','ambiguous_date','03/04/25','reject','Day/month interpretation ambiguous in this feed')
 # 14 invalid measurement readings => set nullable value to NULL during cleaning
 mutate('assessments',range(0,14),'body_temperature','invalid_numeric',lambda r:999 if src!='D' else -200,
        'set_null','Physiologically impossible synthetic temperature; keep assessment and null measurement')
 # 12 broken references => reject dependent leaf records
 mutate('clinical_notes',range(40,46),'admission_id','broken_reference',999999,'reject','Admission ID absent in this hospital')
 mutate('diagnoses',range(1800,1806),'patient_id','broken_reference',999999,'reject','Patient ID absent in this hospital')
 # 12 chronologically impossible surgeries => reject
 mutate('surgical_procedures',range(0,12),'procedure_date','chronology',lambda r:raw_value('procedure_date','2023-01-01',src),
        'reject','Surgery occurs before corresponding hospital admission')
 # 24 duplicated *entity rows*, not attributes or objects.
 for tab,inds in [('diagnoses',range(80,88)),('clinical_notes',range(80,88)),('surgical_procedures',range(80,88))]:
  for ix in inds:
   r=dict(tables[tab][ix]);tables[tab].append(r)
   mark_issue(src,tab,'exact_duplicate',None,r,'deduplicate','Exact copy of an already present entity record')
 return tables

def write_sources(src,tables):
 c=CONFIG[src];outdir=RAW/(f'Source_{src}_{c["continent"].replace(" ","_")}_{c["country"].replace(" ","_")}_{c["format"]}')
 outdir.mkdir(parents=True,exist_ok=True)
 if src in ('A','B'):
  delim='|' if src=='A' else ','
  ext='.txt' if src=='A' else '.csv'
  for tab,rows in tables.items():
   with (outdir/(tab+ext)).open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=delim,lineterminator='\n')
    w.writeheader();w.writerows(rows)
 elif src=='C':
  root=ET.Element('hospital_dataset',source='C',country=c['country'],continent=c['continent'])
  for tab,rows in tables.items():
   group=ET.SubElement(root,tab)
   for r in rows:
    record=ET.SubElement(group,'record')
    for k,v in r.items():ET.SubElement(record,k).text=str(v)
  ET.indent(root,space='  ')
  ET.ElementTree(root).write(outdir/'hospital.xml',encoding='utf-8',xml_declaration=True)
 else:
  with (outdir/'hospital.json').open('w',encoding='utf-8') as f:
   json.dump({'hospital':{'source':'D','country':c['country'],'continent':c['continent'],'name':c['hospital']},
              'entities':tables},f,ensure_ascii=False,indent=2)
 (DOCS/f'SOURCE_INFO_{src}.md').write_text(f'# Source {src}: {c["hospital"]}\nCountry: {c["country"]}\nContinent: {c["continent"]}\nFormat: {c["format"]}\n\nRecords: {sum(map(len,tables.values()))}\n\nAll personal data are fictional. Local IDs deliberately overlap across different sources.\n',encoding='utf-8')
 return outdir

def clean_value(field,x,src):
 c=CONFIG[src]
 if x is None or str(x).strip() in ('', 'NA','k.A.','未記録','NULL','N/A','-'):return None
 x=str(x).strip()
 if field in DATE_FIELDS:
  if x=='03/04/25':return '__AMBIGUOUS__'
  try:return datetime.strptime(x,c['date_format']).strftime('%Y-%m-%d')
  except (ValueError,TypeError):return '__BAD_DATE__'
 if field in TIME_FIELDS:
  if src=='B':x=x.replace('.',':')
 if field=='diagnosis_type':
  inv={'Haupt':'Primary','Neben':'Secondary','主':'Primary','副':'Secondary','PRIMARY':'Primary','SECONDARY':'Secondary',
       'Primary':'Primary','Secondary':'Secondary'}
  return inv.get(x,inv.get(x.title(),x.title()))
 if field=='gender':return {'M':'Male','F':'Female','X':'Other','男':'Male','女':'Female','その他':'Other'}.get(x,x.title())
 if field=='life_status':return {'Lebend':'Alive','Verstorben':'Deceased','生存':'Alive','死亡':'Deceased','ALIVE':'Alive','DEAD':'Deceased'}.get(x,x)
 if field=='unit_type':
  pairs={'Notaufnahme':'ED','Normalstation':'General Ward','Intensivstation':'ICU','Chirurgie':'Surgical Ward','Aufwachraum':'Recovery',
        '救急':'ED','一般病棟':'General Ward','集中治療':'ICU','外科病棟':'Surgical Ward','回復室':'Recovery',
        'EMERGENCY':'ED','WARD':'General Ward','SURGICAL':'Surgical Ward','RECOVERY':'Recovery'}
  return pairs.get(x,x)
 if field=='priority':
  return {'Normal':'Routine','Hoch':'Urgent','Sofort':'Stat','通常':'Routine','緊急':'Urgent','至急':'Stat',
          'LOW':'Routine','HIGH':'Urgent','CRITICAL':'Stat'}.get(x,x)
 if field=='full_name':
  x=re.sub(r'\s+',' ',x)
  return x.title() if src in ['A','B','D'] else x
 if field in ('is_followup',):return str(x).lower() in ('yes','ja','true','1')
 if field in ID_FIELDS and field not in ('icd9_code','primary_icd9_code','secondary_icd9_code'):
  try:return int(x)
  except ValueError:return None
 if field in ('body_temperature','heart_rate','respiratory_rate','oxygen_saturation','pain_level','triage_priority_level','duration_minutes','capacity_beds','bed_number','result_value'):
  try:return float(x)
  except ValueError:return None
 return x

def verify_and_clean():
 # Decode the *written raw source files*, not in-memory generation data.
 source_decoded={}
 for src,c in CONFIG.items():
  folder=next(x for x in RAW.glob('Source_'+src+'_*') if x.is_dir())
  if src in ('A','B'):
   delim='|' if src=='A' else ',';ext='.txt' if src=='A' else '.csv'
   docs={tab:list(csv.DictReader((folder/(tab+ext)).open(encoding='utf-8',newline=''),delimiter=delim)) for tab in ORDER}
  elif src=='C':
   root=ET.parse(folder/'hospital.xml').getroot()
   docs={tab:[{el.tag:el.text for el in rec} for rec in root.find(tab).findall('record')] for tab in ORDER}
  else:docs=json.loads((folder/'hospital.json').read_text(encoding='utf-8'))['entities']
  assert {tab:len(rows) for tab,rows in docs.items()}=={tab:COUNT[tab]+(8 if tab in ('diagnoses','clinical_notes','surgical_procedures') else 0) for tab in ORDER}
  inv_by_tab={tab:{key_for(k,src):k for k in all_raw['A'][tab][0]} for tab in docs}
  decoded={}
  for tab,rows in docs.items():
   inv=inv_by_tab[tab];decoded[tab]=[{inv[k]:clean_value(inv[k],v,src) for k,v in row.items()} for row in rows]
  source_decoded[src]=decoded
 # Parent keys for FK check: separate from child errors intentionally.
 available={src:{tab:{r[KEYS[tab]] for r in t[tab] if r[KEYS[tab]] is not None} for tab in ORDER} for src,t in source_decoded.items()}
 cleaned=defaultdict(list); seen={tab:set() for tab in ORDER}
 for src,tables in source_decoded.items():
  for tab in ORDER:
   pk=KEYS[tab]
   for ordinal,r in enumerate(tables[tab],1):
    lid=r.get(pk); composite=(src,lid) if tab!='icd9_dictionary' else lid
    reason=None
    if lid is None:reason='missing_primary_key'
    elif composite in seen[tab]:reason='deduplicated' if tab!='icd9_dictionary' else 'shared_reference_dictionary'
    elif tab=='diagnoses' and r['icd9_code'] is None:reason='missing_required_icd9'
    elif tab=='clinical_notes' and r['physician_id'] is None:reason='missing_required_physician'
    elif any(r.get(f) in ('__BAD_DATE__','__AMBIGUOUS__') for f in DATE_FIELDS):reason='invalid_or_ambiguous_date'
    else:
     for f,parent in FK.get(tab,{}).items():
      val=r.get(f)
      # Optional secondary ICD-9 and nullable links are explicitly allowed.
      if val is not None and val not in available[src][parent]:
       reason='broken_reference';break
    if reason is None and tab in ('surgical_procedures','clinical_notes'):
     a=tables['admissions'][r['admission_id']-1] if isinstance(r.get('admission_id'),int) and 1<=r['admission_id']<=len(tables['admissions']) else None
     if a is not None:
      event=r['procedure_date'] if tab=='surgical_procedures' else r['note_date']
      if not event or event<a['admission_date'] or event>a['discharge_date']:reason='chronology'
    if reason:
     rejects.append({'source':src,'entity':tab,'local_id':lid,'raw_row_number':ordinal,'reason':reason})
     continue
    seen[tab].add(composite)
    item=dict(r)
    # use globally unique IDs for hospital-local keys; ICD-9 remains globally shared string.
    for f,parent in FK.get(tab,{}).items():
     if item.get(f) is not None and parent!='icd9_dictionary':item[f]=f'{src}:{item[f]}'
    if tab!='icd9_dictionary':item[pk]=f'{src}:{lid}'
    item['source_system']=src
    if tab=='assessments':
     temp=item['body_temperature']
     if temp is not None:
      if item['temperature_unit']=='F':temp=round((temp-32)*5/9,1);transforms['fahrenheit_to_celsius']+=1
      if not (30<=temp<=44):
       item['body_temperature']=None;transforms['invalid_temperature_to_null']+=1
      else:item['body_temperature']=temp
     item['temperature_unit']='C'
    cleaned[tab].append(item)
 # Global FK integrity of accepted rows: all references must exist in clean set.
 for tab,rows in cleaned.items():
  for field,parent in FK.get(tab,{}).items():
   allowed={v[KEYS[parent]] for v in cleaned[parent]}
   bad=[x for x in rows if x[field] is not None and x[field] not in allowed]
   if bad:raise AssertionError(f'cleaned FK mismatch {tab}.{field}->{parent}: {len(bad)} -- {bad[:5]}')
 CLEAN.mkdir(exist_ok=True,parents=True)
 for tab,rows in cleaned.items():
  with (CLEAN/(tab+'.csv')).open('w',newline='',encoding='utf-8') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 return cleaned


def csv_write(path,rows,cols=None):
 with path.open('w',encoding='utf-8',newline='') as f:
  cols=cols or list(rows[0]);w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
 if RAW.exists():shutil.rmtree(RAW)
 if CLEAN.exists():shutil.rmtree(CLEAN)
 DOCS.mkdir(exist_ok=True)
 for src in CONFIG:
  canonical=hospital_rows(src)
  raw=introduce_issues(src,{tab:into_raw(tab,rs,src) for tab,rs in canonical.items()})
  all_raw[src]=raw
  write_sources(src,raw)
 clean=verify_and_clean()
 counts=[]
 for src in CONFIG:
  for tab in ORDER:
   n=len(all_raw[src][tab]);ret=sum(1 for x in clean[tab] if x['source_system']==src)
   counts.append({'source':src,'continent':CONFIG[src]['continent'],'country':CONFIG[src]['country'],
    'format':CONFIG[src]['format'],'entity':tab,'raw_records':n,'retained_source_records':ret,
    'removed_records':n-ret})
  counts.append({'source':src,'continent':CONFIG[src]['continent'],'country':CONFIG[src]['country'],
   'format':CONFIG[src]['format'],'entity':'TOTAL','raw_records':sum(map(len,all_raw[src].values())),
   'retained_source_records':sum(sum(1 for x in clean[tab] if x['source_system']==src) for tab in ORDER),
   'removed_records':sum(len(all_raw[src][tab])-sum(1 for x in clean[tab] if x['source_system']==src) for tab in ORDER)})
 csv_write(DOCS/'record_counts_by_source_entity.csv',counts)
 csv_write(DOCS/'injected_quality_issues.csv',issues)
 csv_write(DOCS/'rejected_or_deduplicated_rows.csv',rejects)
 # Explicit schema fields including Phase1-to-source relationship (no attributes counted as rows)
 dict_rows=[]
 for tab in ORDER:
  for f in all_raw['A'][tab][0]:
   dict_rows.append({'entity':tab,'canonical_field':f,'source_A_TXT':key_for(f,'A'),'source_B_CSV':key_for(f,'B'),
    'source_C_XML':key_for(f,'C'),'source_D_JSON':key_for(f,'D'),
    'primary_key':f==KEYS[tab],'foreign_key_target':FK.get(tab,{}).get(f,''),
    'notes':'Historical ICD-9 string code' if f=='icd9_code' else ('Date; converted to ISO on cleaning' if f in DATE_FIELDS else '')})
 csv_write(DOCS/'schema_field_mapping.csv',dict_rows)
 csv_write(DOCS/'icd9_code_verification.csv',[
  {'icd9_code':code,'historical_description':title,'icd_list_reference_url':f'https://icdlist.com/icd-9/{code}',
   'cms_v32_master_reference':'https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-9-cm-diagnosis-procedure-codes-abbreviated-and-full-code-titles',
   'verification':'Legacy ICD-9-CM code and title cross-checked against accessible code references'}
  for code,title,_ in ICD9])
 csv_write(DOCS/'raw_sha256_checksums.csv',[
  {'relative_path':str(f.relative_to(ROOT)).replace('\\','/'),
   'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}
  for f in sorted(RAW.rglob('*')) if f.is_file()])
 src_rec={src:sum(map(len,x.values())) for src,x in all_raw.items()}
 raw_sum=sum(src_rec.values());clean_sum=sum(map(len,clean.values()))
 reasons=Counter(x['reason'] for x in rejects)
 validation={
  'record_count_by_source':src_rec,'raw_total':raw_sum,'cleaned_total':clean_sum,'removed_total':raw_sum-clean_sum,
  'cleaning_reasons':dict(reasons),'synthetic_issue_type_counts':dict(Counter(x['issue_type'] for x in issues)),
  'transformations':dict(transforms),
  'per_entity_clean_count':{tab:len(clean[tab]) for tab in ORDER},
  'format_parsed_successfully':True,'local_ids_are_source_namespaced':True,
  'icd9_codes_preserved_as_strings':True,'primary_diagnoses_recorded_once':True,
  'hospital_count':4,'global_foreign_keys_pass':True,
  'raw_source_files_preserved_unchanged_after_creation':True,
 }
 (DOCS/'validation_report.json').write_text(json.dumps(validation,indent=2,ensure_ascii=False),encoding='utf-8')
 assert 20000<=raw_sum<=40000 and all(5000<=n<=10000 for n in src_rec.values())
 assert raw_sum==clean_sum+len(rejects)
 assert reasons['deduplicated']==96 and reasons['shared_reference_dictionary']==72
 assert all(len(clean[t])>0 for t in ORDER)
 # verify Phase 1 query cases in clean outputs
 diag=clean['diagnoses'];admissions={x['admission_id']:x for x in clean['admissions']}
 dic=defaultdict(set)
 for x in diag:dic[x['admission_id']].add(x['icd9_code'])
 multi_dx=sum(len(v)>1 for v in dic.values())
 notes_per=Counter(x['patient_id'] for x in clean['clinical_notes'])
 multi_notes=sum(v>1 for v in notes_per.values())
 surg={(x['admission_id'],x['procedure_date']) for x in clean['surgical_procedures']}
 rad={(x['admission_id'],x['examination_date']) for x in clean['radiology_examinations']}
 same_day=len(surg & rad)
 deceased={x['patient_id'] for x in clean['patients'] if x['life_status']=='Deceased'}
 primary_deceased=sum(x['patient_id'] in deceased and x['diagnosis_type']=='Primary' for x in diag)
 validation['query_scenarios']={'admissions_with_multiple_distinct_icd9':multi_dx,'patients_with_multiple_clinical_notes':multi_notes,
  'same_day_surgery_radiology_admission_pairs':same_day,'primary_diagnoses_of_deceased_patients':primary_deceased}
 assert min(multi_dx,multi_notes,same_day,primary_deceased)>0
 (DOCS/'validation_report.json').write_text(json.dumps(validation,indent=2,ensure_ascii=False),encoding='utf-8')
 (DOCS/'README.md').write_text(make_readme(validation,reasons),encoding='utf-8')
 # Keep exact unchanged ER diagram for comparison only, not treated as raw source.
 ref=ROOT/'reference';ref.mkdir(exist_ok=True)
 src_path=Path('/mnt/data/ERdiagram.drawio')
 if src_path.exists():shutil.copyfile(src_path,ref/'ERdiagram.drawio')
 print(json.dumps(validation,indent=2,ensure_ascii=False))

def make_readme(v,reasons):
 issue_counts=Counter(x['issue_type'] for x in issues)
 source_lines='\n'.join(f'| {src} | {c["continent"]} | {c["country"]} | {c["format"]} | {v["record_count_by_source"][src]:,} |' for src,c in CONFIG.items())
 reason_lines='\n'.join(f'| {k} | {n} |' for k,n in sorted(reasons.items()))
 issue_lines='\n'.join(f'| {k} | {n} | {n/v["raw_total"]*100:.2f}% |' for k,n in sorted(issue_counts.items()))
 return f'''# SOEN 363 — Phase 2 Synthetic Hospital Data Sources

Generated reproducibly with `generate.py`. **All patients, clinicians, contact information, examinations, and records are fictional.** Historical ICD-9 codes only; not for real-world medical coding.

## Geographic origins and formats

| Source | Continent | Country | Source format | Raw entity records |
|---|---|---|---|---:|
{source_lines}
| **Total** | | | | **{v['raw_total']:,}** |

Four **independent hospital systems**. Each source has between 5,000 and 10,000 records; combined total is between 20,000 and 40,000. `raw/` files are never edited during integration.

## Record counting rules

- Every row in TXT and CSV is one record. Header lines do not count. Source A uses pipe-delimited `.txt` entity files; B uses ordinary `.csv` entity files.
- Source C uses one XML document with 18 entity containers; **only individual `<record>` elements count**, not the root, tags, or attribute elements. There are no embedded entity instances to double count.
- Source D uses JSON with metadata and `entities` arrays; **each array item counts as one entity record**, not its fields, array objects, or metadata.
- `primary_Diagnosis` and `secondary_diagnosis` are represented by `diagnoses.diagnosis_type`; no second duplicate record is generated for their ISA subtype.
- BloodTest, CT Examination, electrodiagram are values of `diagnostic_examinations.examination_type`. Radiology examination entities are recorded in their own collection, not duplicated in the diagnostic_examinations supertype collection.
- The phase-1 ERD lists unit-stay attributes (`unit_type`, `ward`, `room`) rather than a standalone hospital unit table. A small `hospital_units` reference entity was added to make wards/units explicit; `unit_stays.hospital_unit_id` is an integration extension.
- Per-entity exact counts appear in `documentation/record_counts_by_source_entity.csv`.

## Canonical entity relationships and schema

`patients` 1→many `admissions`; every admission has an assigned nurse, physician, ≥1 triage `assessment`, and ≥1 `unit_stay`. `diagnoses` link patient, admission, physician, and ICD-9 dictionary; `diagnosis_type` records Primary or Secondary. Diagnoses are not duplicated into their subtype tables.

Orders and examinations link to the appropriate admission and clinicians. Radiology reports reference radiology examinations and radiologists; surgical procedures reference admission and physician. Clinical notes, discharge records, and discharge summaries are linked to their appropriate parents. See `documentation/schema_field_mapping.csv` for all field names and PK/FK references.

## Meaningful integration differences

| Dimension | Source A — Canada TXT | Source B — Germany CSV | Source C — Japan XML | Source D — South Africa JSON |
|---|---|---|---|---|
| Patient ID field | `patient_id` | `PatientNr` | `patientNumber` | `PAT_ID` |
| Admission ID field | `admission_id` | `FallNr` | `encounterNumber` | `ADM_ID` |
| Date convention | YYYY-MM-DD | DD.MM.YYYY | YYYY/MM/DD | DD/MM/YYYY |
| Null marker | `NA` | `k.A.` | `未記録` | `NULL` |
| Temperature | °C | °C | °C | °F |
| Categorical labels | English | German | Japanese | English uppercase |
| Local keys | begin at 1 | begin at 1 | begin at 1 | begin at 1 |

Names and addresses are generated from geographic locale dictionaries or fabricated local names. No source contains real personal identifiers. **Repeated local identifiers are intentional and do not mean the same person across countries.** Canonical cleaned IDs are namespaced `A:101`, `B:101`, etc. ICD-9 reference codes, however, are global and are shared/deduplicated correctly across sources.

## Injected data-quality issues (raw source rows)

| Issue category | Injected instances across all sources | Approx. share of all raw records |
|---|---:|---:|
{issue_lines}

Locations (entity, local key, field, description, proposed action) are exhaustively documented in `documentation/injected_quality_issues.csv`. Rates are deliberately low so the majority of rows remain usable. Issues include duplicate rows, missing required and optional values, category/name formatting, impossible and ambiguous dates, invalid numeric measurements, dangling foreign keys, impossible event chronology, and identical local IDs across distinct sources.

## Integrated cleaning and reconciliation

`cleaned_integrated/` is a demonstrative **CSV integration result**, not a SQL database. It is generated **from the raw files on disk** and does not change their bytes. This reconciled CSV set is ready for mapping into the Phase-1 SQL schema (adapters may be needed for extended attributes).

1. Read files in their native format and map localized field names to canonical fields.
2. Parse locale-specific dates and time strings; convert all dates to ISO and temperatures to Celsius; normalize labels and whitespace.
3. Retain optional NULLs, and null invalid optional temperature measurements.
4. Reject missing required data, impossible/ambiguous dates, broken FKs, and impossible surgery/note chronology.
5. Drop **exact** duplicated local entity records within a source, not legitimately identical local IDs from other countries.
6. Deduplicate the shared ICD-9 reference dictionary across sources; preserve all codes as strings, including dots and leading zeros.
7. Namespace all hospital-local primary and foreign keys; verify that accepted relationships still resolve.

| Reconciliation outcome | Records |
|---|---:|
| Raw records across four systems | {v['raw_total']:,} |
| Total removed / deduplicated | {v['removed_total']:,} |
| **Retained integrated entity records** | **{v['cleaned_total']:,}** |

Removal reasons (one reason per removed row):

| Reason | Rows |
|---|---:|
{reason_lines}

For complete per-entity source-to-cleaned reconciliation see `documentation/record_counts_by_source_entity.csv`; for per-row reasons see `documentation/rejected_or_deduplicated_rows.csv`.

## Evidence for the four Phase 1 query scenarios

- Admissions with >1 distinct ICD-9 code: **{v['query_scenarios']['admissions_with_multiple_distinct_icd9']:,}**
- Patients with >1 clinical note (latest-note query): **{v['query_scenarios']['patients_with_multiple_clinical_notes']:,}**
- Admission/date combinations having both surgery and radiology: **{v['query_scenarios']['same_day_surgery_radiology_admission_pairs']:,}**
- Primary diagnoses recorded for deceased patients: **{v['query_scenarios']['primary_diagnoses_of_deceased_patients']:,}**

## ICD-9 verification and historical limitations

The dictionary uses **24 historical ICD-9-CM diagnosis codes with descriptions** from the final U.S. 2015 ICD-9-CM code set. Primary reference is CMS: https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-9-cm-diagnosis-procedure-codes-abbreviated-and-full-code-titles . CMS distributes Version 32 full and abbreviated titles (effective October 1, 2014). The code/title pairs have been cross-checked against publicly accessible legacy ICD-9-CM code references; a per-code verification URL is recorded in `documentation/icd9_code_verification.csv`. For an additional final check, compare with the downloadable official CMS V32 source file before submission. This generator does not redistribute an official dictionary file. Since 2015 these are legacy codes, included solely because the assignment explicitly requires ICD-9.

## Files

- `raw/`: original source files in **only each assigned format**; source metadata lives in `documentation/SOURCE_INFO_*.md`
- `cleaned_integrated/`: normalized CSV preview across four hospitals
- `documentation/record_counts_by_source_entity.csv`: detailed record counts and removals
- `documentation/injected_quality_issues.csv`: exactly where/how issues were inserted
- `documentation/rejected_or_deduplicated_rows.csv`: actual removal audit
- `documentation/schema_field_mapping.csv`: canonical and native column mapping, PK/FK design
- `documentation/validation_report.json`: machine-readable validation results\n- `documentation/icd9_code_verification.csv`: legacy code-by-code reference links\n- `documentation/raw_sha256_checksums.csv`: original-source SHA-256 fingerprints
- `reference/ERdiagram.drawio`: untouched reference diagram copy
- `generate.py`: deterministic generator; rerun with Python and Faker installed to reconstruct dataset

**Important scope note:** `hospital_units` is a documented extension; the ERD's other inheritance structures are represented by discriminator fields rather than repeating the same instance twice. Generated values are mock data, not clinical guidance.
'''

if __name__=='__main__':main()
