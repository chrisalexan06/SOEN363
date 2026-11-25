"""Check query coverage on accepted CSVs (not a replacement for Tasks 5 or 6)."""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / 'task2_output'
CRITICAL = {'ICU', 'CCU', 'MICU', 'SICU'}

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as file:
        return list(csv.DictReader(file))

def group(rows, key):
    result = defaultdict(list)
    for row in rows:
        result[row[key]].append(row)
    return result

def main():
    counts = read(OUTPUT / 'cleaning_summary.csv')
    result = {}
    for source in 'ABCD':
        t = {p.stem: read(p) for p in (OUTPUT / 'cleaned' / source).glob('*.csv')}
        adm = {r['admission_id']: r for r in t['admissions']}
        patients = {r['patient_id']: r for r in t['patients']}
        stays = group(t['unit_stays'], 'admission_id')
        surgeries = group(t['surgical_procedures'], 'admission_id')
        radiology = group(t['radiology_examinations'], 'admission_id')
        diagnoses = group(t['diagnoses'], 'admission_id')
        bypatient = group(t['admissions'], 'patient_id')
        radparents = {r['examination_id']: r for r in t['diagnostic_examinations']}
        discharge = {r['admission_id']: r for r in t['discharge_records']}
        critical = {a: [r for r in rows if r['unit_type'] in CRITICAL] for a, rows in stays.items()}
        raw = sum(int(r['input_records']) for r in counts if r['source']==source)
        accepted = sum(int(r['accepted']) for r in counts if r['source']==source)
        quarantined = sum(int(r['quarantined']) for r in counts if r['source']==source)
        duplicates = sum(int(r['duplicate_removed']) for r in counts if r['source']==source)
        assert 5000 <= raw <= 10000 and raw == accepted + quarantined + duplicates
        assert accepted == sum(map(len,t.values()))
        assert all(a['admission_source'] for a in adm.values())
        assert all(r['examination_id'] in radparents and radparents[r['examination_id']]['admission_id']==r['admission_id'] for r in t['radiology_examinations'])
        assert all(r['admission_status']=='Closed' for a in discharge for r in [adm[a]])
        assert all(adm[a]['discharge_timestamp']==r['discharge_timestamp'] for a,r in discharge.items())
        assert all(any(d['diagnosis_type']=='Primary' for d in diagnoses[a]) for a,r in adm.items() if r['admission_status']=='Closed')
        dead = [r for r in discharge.values() if r['patient_condition']=='Deceased']
        assert all(patients[r['patient_id']]['date_of_death']==r['discharge_date'] for r in dead)
        coverage = {
            'Q1_high_priority_emergency': sum(adm[r['admission_id']]['admission_type']=='Emergency' and int(r['triage_priority_level'])<=2 for r in t['assessments']),
            'Q2_patients_more_than_three_admissions': sum(len(x)>3 for x in bypatient.values()),
            'Q3_discharged_without_surgery': sum(r['admission_status']=='Closed' and a not in surgeries for a,r in adm.items()),
            'Q4_radiology_and_surgery': len(set(radiology)&set(surgeries)),
            'Q5_icu_ccu_stays_over_seven_days': sum(r['unit_type'] in {'ICU','CCU'} and r['exit_timestamp'] and datetime.fromisoformat(r['exit_timestamp'])-datetime.fromisoformat(r['entry_timestamp'])>timedelta(days=7) for r in t['unit_stays'] if r['exit_timestamp']),
            'Q6_patients_without_admissions': len(set(patients)-set(bypatient)),
            'Q7_ed_to_icu_ccu': sum(adm[a]['admission_source']=='Emergency Department' and any(x['unit_type']=='ED' and x['entry_timestamp']<y['entry_timestamp'] for x in stays[a] for y in rows if y['unit_type'] in {'ICU','CCU'}) for a,rows in critical.items()),
            'Q8_primary_diagnosis_with_icu_ccu': sum(any(x['diagnosis_type']=='Primary' for x in diagnoses[a]) and any(x['unit_type'] in {'ICU','CCU'} for x in rows) for a,rows in critical.items()),
            'Q9_critical_care_types': len({r['unit_type'] for r in t['unit_stays']} & CRITICAL),
            'Q10_surgery_before_icu_ccu': sum(any(x['procedure_timestamp']<y['entry_timestamp'] for x in surgeries[a] for y in rows if y['unit_type'] in {'ICU','CCU'}) for a,rows in critical.items()),
            'Q11_patients_without_radiology': len(set(patients)-{adm[a]['patient_id'] for a in radiology}),
            'Q12_recovery_summary_notes': sum(r['note_type']=='Discharge Summary' and 'recovery' in r['note_contents'].lower() for r in t['clinical_notes']),
            'Q13_radiology_without_icu_ccu': sum(not any(r['unit_type'] in {'ICU','CCU'} for r in stays[a]) for a in radiology),
            'Q14_completed_stays': sum(r['admission_status']=='Closed' and bool(r['discharge_timestamp']) for r in adm.values()),
            'Q15_admissions_with_transfers': sum(len(x)>1 for x in stays.values()),
            'Q16_multiple_critical_care_types': sum(len({r['unit_type'] for r in rows})>1 for rows in critical.values()),
            'Q17_multiple_diagnosis_codes': sum(len({r['icd9_code'] for r in rows})>1 for rows in diagnoses.values()),
            'Q18_patients_with_complete_notes': len({r['patient_id'] for r in t['clinical_notes'] if r['note_type'] and r['note_contents'] and r['note_timestamp']}),
            'Q19_death_during_hospitalization': len(dead),
            'Q20_same_day_surgery_radiology': sum(any(x['procedure_date']==y['examination_date'] for x in surgeries[a] for y in rows) for a,rows in radiology.items()),
        }
        result[source] = dict(raw=raw, accepted=accepted, quarantined=quarantined, duplicates=duplicates,
                              open_admissions=sum(r['admission_status']=='Open' for r in adm.values()),
                              closed_without_separate_discharge_record=sum(r['admission_status']=='Closed' and a not in discharge for a,r in adm.items()),
                              query_coverage=coverage)
    assert all(sum(r['query_coverage'][q] for r in result.values())>0 for q in result['A']['query_coverage'])
    assert 20000 <= sum(r['raw'] for r in result.values()) <= 40000
    print(json.dumps(result, indent=2))
    (OUTPUT / 'revision_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
