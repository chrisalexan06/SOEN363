import csv
import json
from collections import defaultdict, Counter
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
INPUT = BASE / 'task2_output' / 'cleaned'
OUTPUT = BASE / 'task3_output'
SCHEMA = BASE / 'task2_output' / 'integrated_schema.sql'
SOURCES = 'ABCD'
# Source entity -> (target table, source primary key, target primary key)
ENTITIES = {
    'physicians': ('physician','physician_id','physician_id'),
    'nurses': ('nurse','nurse_id','nurse_id'),
    'radiologists': ('radiologist','radiologist_id','radiologist_id'),
    'hospital_units': ('hospital_unit','unit_id','hospital_unit_id'),
    'patients': ('patient','patient_id','patient_id'),
    'admissions': ('admission','admission_id','admission_id'),
    'diagnoses': ('diagnosis','diagnosis_id','diagnosis_id'),
    'diagnostic_orders': ('diagnostic_order','diagnostic_order_id','diagnostic_order_id'),
    'unit_stays': ('unit_stay','unit_stay_id','unit_stay_id'),
    'surgical_procedures': ('surgical_procedure','procedure_id','procedure_id'),
    'clinical_notes': ('clinical_note','clinical_note_id','clinical_note_id'),
    'assessments': ('assessment','assessment_id','assessment_id'),
    'diagnostic_examinations': ('diagnostic_examination','examination_id','examination_id'),
    'radiology_examinations': ('radiology_examination','radiology_examination_id','examination_id'),
    'discharge_records': ('discharge_record','discharge_record_id','discharge_record_id'),
    'radiology_reports': ('radiology_report','radiology_report_id','radiology_report_id'),
    'discharge_summaries': ('discharge_summary','discharge_summary_id','discharge_summary_id'),
}
ALIASES = {
    'diagnostic_order': {'requesting_physician':'requesting_physician_id','clinical_reason':'clinical_reason_for_examination'},
    'clinical_note': {'note_creation_date':'note_date','note_creation_time':'note_time'},
    'radiology_report': {'interpretation':'interpretations'},
    'discharge_record': {'scheduled_follow_up_appointment':'follow_up_appointment','responsible_physician_name':'responsible_physician','responsible_physician_id':'physician_id'},
    'discharge_summary': {'responsible_physician_id':'physician_id','icd9_coded_diagnoses':'icd9_code_diagnoses'},
    'admission': {'followup_description':'past_record_followup'},
}
REFERENCES = {
    'patient_id':'patients','admission_id':'admissions','physician_id':'physicians','nurse_id':'nurses',
    'radiologist_id':'radiologists','requesting_physician':'physicians','referring_physician_id':'physicians',
    'responsible_physician_id':'physicians','reviewed_by_radiologist_id':'radiologists',
    'hospital_unit_id':'hospital_units','diagnostic_order_id':'diagnostic_orders',
    'radiology_examination_id':'radiology_examinations','discharge_record_id':'discharge_records',
}

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return [{k: v if v != '' else None for k,v in r.items()} for r in csv.DictReader(f)]

def schema_columns():
    sql = SCHEMA.read_text(encoding='utf-8-sig')
    tables = {}
    for name, body in re.findall(r'CREATE TABLE phase2\.(\w+)\s*\((.*?)\n\);',sql,re.S|re.I):
        columns = {}
        for line in body.splitlines():
            line = line.strip().rstrip(',')
            if not line or line.split()[0].upper() in {'CONSTRAINT','UNIQUE','CHECK','FOREIGN','PRIMARY'} or line.startswith(('CHECK (','UNIQUE (')):
                continue
            col = line.split()[0]
            columns[col] = 'NOT NULL' in line.upper() or 'PRIMARY KEY' in line.upper()
        tables[name.lower()] = columns
    if len(tables)!=32:
        raise ValueError(f'Expected 32 schema tables, found {len(tables)}')
    return tables

def main():
    columns = schema_columns()
    data = {e:{s:read_csv(INPUT/s/f'{e}.csv') for s in SOURCES} for e in [*ENTITIES,'icd9_dictionary']}
    ids = {}
    for e,(_,pk,_) in ENTITIES.items():
        if e=='radiology_examinations': continue
        keys=[(s,r[pk]) for s in SOURCES for r in sorted(data[e][s],key=lambda r:int(r[pk]))]
        if len(keys)!=len(set(keys)): raise ValueError(f'Duplicate source key: {e}')
        ids[e]={k:i for i,k in enumerate(keys,1)}
    ids['radiology_examinations']={}
    for s in SOURCES:
        for r in data['radiology_examinations'][s]:
            k=(s,r['radiology_examination_id'])
            if k in ids['radiology_examinations']: raise ValueError(f'Duplicate radiology key {k}')
            ids['radiology_examinations'][k]=ids['diagnostic_examinations'][(s,r['examination_id'])]
    out={t:[] for t in columns}
    def add(t,r):
        unknown=set(r)-set(columns[t])
        if unknown: raise ValueError(f'{t}: unknown columns {unknown}')
        row={k:r.get(k) for k in columns[t]}
        missing=[k for k,required in columns[t].items() if required and row[k] is None]
        if missing: raise ValueError(f'{t}: required fields missing {missing}: {row}')
        out[t].append(row)
        return row
    def ref(e,s,v):
        return None if v is None else ids[e][s,v]
    def subset(r,names): return {k:r[k] for k in names.split()}
    for s,country,continent,fmt in [('A','Canada','North America','TXT'),('B','Germany','Europe','CSV'),('C','Japan','Asia','XML'),('D','South Africa','Africa','JSON')]:
        add('source_system',dict(source_id=s,hospital_name=f'Synthetic Hospital {s}',country=country,continent=continent,file_format=fmt))
    dictionary={}
    for s in SOURCES:
        for r in data['icd9_dictionary'][s]:
            code=r['icd9_code']
            if code in dictionary and dictionary[code]!=r: raise ValueError(f'Conflicting ICD-9 entry {code} in {s}')
            dictionary[code]=r
            add('icd9_source_mapping',dict(source_id=s,original_code=code,icd9_code=code))
    for r in dictionary.values(): add('icd9_dictionary',r)
    diagnoses=defaultdict(list)
    unresolved=[]
    medications={}
    def med(name):
        if not name or name.casefold() in {'none','none documented'}: return None
        key=name.casefold()
        if key not in medications:
            medications[key]=len(medications)+1
            add('medication',dict(medication_id=medications[key],medication_name=name))
        return medications[key]
    def junction(t,**r): add(t,r)
    for e,(t,pk,gpk) in ENTITIES.items():
        for s in SOURCES:
            for raw in sorted(data[e][s],key=lambda r:int(r[pk])):
                global_id=ref(e,s,raw[pk])
                row={gpk:global_id,'source_id':s,'original_id':raw[pk]}
                for col in columns[t]:
                    if col in row: continue
                    if col in {'past_record_followup','primary_diagnosis_id'}: continue
                    val=raw.get(ALIASES.get(t,{}).get(col,col))
                    row[col]=ref(REFERENCES[col],s,val) if col in REFERENCES else val
                if t=='discharge_record':
                    matches=diagnoses[(s,raw['admission_id'],raw['primary_icd9_code'],'Primary')]
                    if len(matches)!=1: raise ValueError(f'Ambiguous/missing primary diagnosis {s} {raw[pk]}: {matches}')
                    row['primary_diagnosis_id']=matches[0]
                row=add(t,row)
                if t=='diagnosis':
                    kind=raw['diagnosis_type']
                    if kind not in {'Primary','Secondary'}: raise ValueError(kind)
                    diagnoses[s,raw['admission_id'],raw['icd9_code'],kind].append(global_id)
                    add(kind.lower()+'_diagnosis',subset(row,'diagnosis_id icd9_code diagnosis_date diagnosis_time patient_id admission_id'))
                elif t=='assessment':
                    for field,target,attr in [('reported_symptoms','assessment_reported_symptoms','reported_symptom'),('known_allergies','assessment_known_allergies','known_allergy')]:
                        val=raw[field]
                        if val and val.casefold()!='none': junction(target,assessment_id=global_id,patient_id=row['patient_id'],**{attr:val})
                    m=med(raw['current_medication'])
                    if m is not None: junction('current_meds',current_id=len(out['current_meds'])+1,med_id=m,assessment_id=global_id,patient_id=row['patient_id'])
                elif t=='diagnostic_examination':
                    subtype={'BloodTest':'blood_test','CT Examination':'ct_examination','electrodiagram':'electrodiagram'}.get(raw['examination_type'])
                    if subtype: add(subtype,subset(row,'examination_id examination_status examination_time examination_date body_area_examined referring_physician_id'))
                elif t=='discharge_record':
                    junction('discharge_record_primary_diagnosis',discharge_record_id=global_id,primary_diagnosis_id=row['primary_diagnosis_id'])
                    if raw['secondary_icd9_code']:
                        matches=diagnoses[s,raw['admission_id'],raw['secondary_icd9_code'],'Secondary']
                        if len(matches)!=1:
                            unresolved.append(dict(source_id=s,original_discharge_id=raw[pk],integrated_discharge_id=global_id,secondary_icd9_code=raw['secondary_icd9_code'],reason='No unique matching secondary diagnosis in same admission',candidate_ids=matches))
                        else:
                            junction('discharge_record_secondary_diagnosis',discharge_record_id=global_id,secondary_diagnosis_id=matches[0])
                    m=med(raw['prescribed_medication'])
                    if m is not None: junction('prescribed_meds',prescribed_id=len(out['prescribed_meds'])+1,med_id=m,prescribed_to_id=global_id,patient_id=ref('patients',s,raw['patient_id']))
    # Validate relationships and unique keys using the actual SQL declarations.
    sql=SCHEMA.read_text(encoding='utf-8-sig')
    indexed={}
    def values(table,cols):
        key=table,tuple(cols)
        if key not in indexed: indexed[key]={tuple(str(r[c]) if r[c] is not None else None for c in cols) for r in out[table]}
        return indexed[key]
    for table,body in re.findall(r'CREATE TABLE phase2\.(\w+)\s*\((.*?)\n\);',sql,re.S|re.I):
        table=table.lower()
        for keys in re.findall(r'(?:PRIMARY KEY|UNIQUE)\s*\(([^)]+)\)',body,re.I):
            cols=[c.strip() for c in keys.split(',')]
            nonnull=[tuple(str(r[c]) for c in cols) for r in out[table] if all(r[c] is not None for c in cols)]
            if len(nonnull)!=len(set(nonnull)): raise ValueError(f'Duplicate key {table} {cols}')
        for line in body.splitlines():
            m=re.search(r'FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES phase2\.(\w+)\(([^)]+)\)',line,re.I)
            if m: local,parent,remote=m.groups(); local=[x.strip() for x in local.split(',')]
            else:
                m=re.search(r'^\s*(\w+)\s+.*?REFERENCES phase2\.(\w+)\(([^)]+)\)',line,re.I)
                if not m: continue
                col,parent,remote=m.groups(); local=[col]
            target=values(parent.lower(),[x.strip() for x in remote.split(',')])
            for r in out[table]:
                key=tuple(str(r[c]) if r[c] is not None else None for c in local)
                if None not in key and key not in target: raise ValueError(f'Unresolved foreign key {table} {local}: {key}')
    admissions={r['admission_id']:r for r in out['admission']}
    for t in ('assessment','diagnosis','diagnostic_order','clinical_note'):
        for r in out[t]:
            if r['patient_id']!=admissions[r['admission_id']]['patient_id']: raise ValueError(f'Patient/admission mismatch {t}: {r}')
    OUTPUT.mkdir(exist_ok=True)
    for t,rows in out.items():
        with (OUTPUT/f'{t}.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(columns[t]));w.writeheader();w.writerows(rows)
    with (OUTPUT/'identifier_mapping.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['entity','source_id','original_id','integrated_id'])
        for e,mapping in ids.items():
            for (s,local),gid in mapping.items():w.writerow([e,s,local,gid])
    summary={'accepted_input_records':sum(len(rows) for sources in data.values() for rows in sources.values()),'integrated_table_rows':{t:len(rows) for t,rows in out.items()},'total_integrated_rows':sum(map(len,out.values())),'identifier_mappings':sum(map(len,ids.values())),'unresolved_secondary_links':len(unresolved),'validation':'Foreign keys, table-level unique keys, required columns and patient/admission consistency checked locally; PostgreSQL checks remain for import.'}
    (OUTPUT/'unresolved_secondary_links.json').write_text(json.dumps(unresolved,indent=2),encoding='utf-8')
    (OUTPUT/'integration_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()