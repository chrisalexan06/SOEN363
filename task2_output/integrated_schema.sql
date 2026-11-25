BEGIN;
CREATE SCHEMA phase2;
REVOKE ALL ON SCHEMA phase2 FROM PUBLIC;

CREATE TABLE phase2.icd9_dictionary (
  icd9_code character varying NOT NULL,
  diagnosis_title character varying NOT NULL,
  description text NOT NULL,
  disease_category character varying NOT NULL,
  CONSTRAINT icd9_dictionary_pkey PRIMARY KEY (icd9_code)
);

CREATE TABLE phase2.medication (
  medication_id integer NOT NULL,
  medication_name character varying,
  CONSTRAINT medication_pkey PRIMARY KEY (medication_id)
);

CREATE TABLE phase2.source_system (
  source_id character(1) PRIMARY KEY CHECK (source_id IN ('A','B','C','D')),
  hospital_name text NOT NULL,
  country text NOT NULL,
  continent text NOT NULL,
  file_format text NOT NULL
);

CREATE TABLE phase2.physician (
  physician_id integer NOT NULL,
  physician_name character varying NOT NULL,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  CONSTRAINT physician_pkey PRIMARY KEY (physician_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, physician_id)
);

CREATE TABLE phase2.nurse (
  nurse_id integer NOT NULL,
  nurse_name character varying NOT NULL,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  CONSTRAINT nurse_pkey PRIMARY KEY (nurse_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, nurse_id)
);

CREATE TABLE phase2.radiologist (
  radiologist_id integer NOT NULL,
  radiologist_name character varying NOT NULL,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  CONSTRAINT radiologist_pkey PRIMARY KEY (radiologist_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, radiologist_id)
);

CREATE TABLE phase2.hospital_unit (
  hospital_unit_id integer PRIMARY KEY,
  unit_name text NOT NULL,
  unit_type text NOT NULL,
  ward text NOT NULL,
  capacity_beds integer NOT NULL CHECK (capacity_beds > 0),
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, hospital_unit_id)
);

CREATE TABLE phase2.icd9_source_mapping (
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_code character varying NOT NULL,
  icd9_code character varying NOT NULL REFERENCES phase2.icd9_dictionary(icd9_code),
  PRIMARY KEY (source_id, original_code)
);

CREATE TABLE phase2.patient (
  patient_id integer NOT NULL,
  full_name character varying NOT NULL,
  date_of_birth date NOT NULL,
  gender character varying NOT NULL,
  health_insurance_number character varying NOT NULL UNIQUE,
  emergency_contact_info character varying,
  telephone_number character varying,
  address character varying,
  life_status character varying NOT NULL,
  physician_id integer,
  nurse_id integer,
  date_of_death date,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  CONSTRAINT patient_pkey PRIMARY KEY (patient_id),
  CONSTRAINT patient_physician_id_fkey FOREIGN KEY (physician_id) REFERENCES phase2.physician(physician_id),
  CONSTRAINT patient_nurse_id_fkey FOREIGN KEY (nurse_id) REFERENCES phase2.nurse(nurse_id),
  UNIQUE (source_id, original_id),
  CHECK (life_status IN ('Alive','Deceased')),
  CHECK ((life_status = 'Alive' AND date_of_death IS NULL) OR (life_status = 'Deceased' AND date_of_death IS NOT NULL AND date_of_death >= date_of_birth)),
  UNIQUE (source_id, patient_id),
  FOREIGN KEY (source_id, physician_id) REFERENCES phase2.physician(source_id, physician_id),
  FOREIGN KEY (source_id, nurse_id) REFERENCES phase2.nurse(source_id, nurse_id)
);

CREATE TABLE phase2.admission (
  admission_id integer NOT NULL,
  patient_id integer NOT NULL,
  professional_name character varying,
  insurance_information character varying,
  admission_type character varying NOT NULL,
  visit_reason text NOT NULL,
  admission_time time without time zone NOT NULL,
  patient_condition character varying,
  admission_date date NOT NULL,
  admission_source character varying NOT NULL,
  care_pathway character varying,
  admission_status character varying NOT NULL,
  nurse_id integer,
  is_followup boolean NOT NULL DEFAULT false,
  past_record_followup integer,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  physician_id integer REFERENCES phase2.physician(physician_id),
  discharge_date date,
  discharge_time time without time zone,
  followup_description text,
  CONSTRAINT admission_pkey PRIMARY KEY (admission_id),
  CONSTRAINT admission_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id),
  CONSTRAINT admission_nurse_id_fkey FOREIGN KEY (nurse_id) REFERENCES phase2.nurse(nurse_id),
  CONSTRAINT fk_past_record_followup FOREIGN KEY (past_record_followup) REFERENCES phase2.admission(admission_id),
  UNIQUE (source_id, original_id),
  CHECK (admission_status IN ('Open','Closed')),
  CHECK ((admission_status = 'Open' AND discharge_date IS NULL AND discharge_time IS NULL) OR (admission_status = 'Closed' AND discharge_date IS NOT NULL AND discharge_time IS NOT NULL AND (discharge_date + discharge_time) >= (admission_date + admission_time))),
  CHECK (admission_type IN ('Emergency','Elective')),
  UNIQUE (source_id, admission_id),
  FOREIGN KEY (source_id, patient_id) REFERENCES phase2.patient(source_id, patient_id),
  FOREIGN KEY (source_id, nurse_id) REFERENCES phase2.nurse(source_id, nurse_id),
  FOREIGN KEY (source_id, past_record_followup) REFERENCES phase2.admission(source_id, admission_id),
  FOREIGN KEY (source_id, physician_id) REFERENCES phase2.physician(source_id, physician_id)
);

CREATE TABLE phase2.diagnosis (
  diagnosis_id integer NOT NULL,
  icd9_code character varying NOT NULL,
  diagnosis_date date NOT NULL,
  diagnosis_time time without time zone NOT NULL,
  diagnosis_type character varying NOT NULL,
  patient_id integer NOT NULL,
  admission_id integer NOT NULL,
  physician_id integer NOT NULL,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  CONSTRAINT diagnosis_pkey PRIMARY KEY (diagnosis_id),
  CONSTRAINT diagnosis_icd9_code_fkey FOREIGN KEY (icd9_code) REFERENCES phase2.icd9_dictionary(icd9_code),
  CONSTRAINT diagnosis_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id),
  CONSTRAINT diagnosis_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id),
  CONSTRAINT diagnosis_physician_id_fkey FOREIGN KEY (physician_id) REFERENCES phase2.physician(physician_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, diagnosis_id),
  FOREIGN KEY (source_id, patient_id) REFERENCES phase2.patient(source_id, patient_id),
  FOREIGN KEY (source_id, admission_id) REFERENCES phase2.admission(source_id, admission_id),
  FOREIGN KEY (source_id, physician_id) REFERENCES phase2.physician(source_id, physician_id)
);

CREATE TABLE phase2.diagnostic_order (
  diagnostic_order_id integer NOT NULL,
  patient_id integer NOT NULL,
  admission_id integer NOT NULL,
  requesting_physician integer NOT NULL,
  requested_examination character varying NOT NULL,
  request_date date NOT NULL,
  request_time time without time zone NOT NULL,
  clinical_reason text NOT NULL,
  priority character varying NOT NULL,
  order_status character varying NOT NULL,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  CONSTRAINT diagnostic_order_pkey PRIMARY KEY (diagnostic_order_id),
  CONSTRAINT diagnostic_order_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id),
  CONSTRAINT diagnostic_order_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id),
  CONSTRAINT diagnostic_order_requesting_physician_fkey FOREIGN KEY (requesting_physician) REFERENCES phase2.physician(physician_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, diagnostic_order_id),
  FOREIGN KEY (source_id, patient_id) REFERENCES phase2.patient(source_id, patient_id),
  FOREIGN KEY (source_id, admission_id) REFERENCES phase2.admission(source_id, admission_id),
  FOREIGN KEY (source_id, requesting_physician) REFERENCES phase2.physician(source_id, physician_id)
);

CREATE TABLE phase2.unit_stay (
  unit_stay_id integer NOT NULL,
  admission_id integer NOT NULL,
  unit_type character varying NOT NULL,
  ward character varying NOT NULL,
  room character varying NOT NULL,
  bed_number character varying NOT NULL,
  entry_date date NOT NULL,
  entry_time time without time zone NOT NULL,
  exit_date date,
  exit_time time without time zone,
  responsible_physician_id integer,
  transfer_reason text,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  hospital_unit_id integer NOT NULL REFERENCES phase2.hospital_unit(hospital_unit_id),
  CONSTRAINT unit_stay_pkey PRIMARY KEY (unit_stay_id),
  CONSTRAINT unit_stay_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id),
  CONSTRAINT unit_stay_responsible_physician_id_fkey FOREIGN KEY (responsible_physician_id) REFERENCES phase2.physician(physician_id),
  UNIQUE (source_id, original_id),
  CHECK ((exit_date IS NULL AND exit_time IS NULL) OR (exit_date IS NOT NULL AND exit_time IS NOT NULL AND (exit_date + exit_time) >= (entry_date + entry_time))),
  UNIQUE (source_id, unit_stay_id),
  FOREIGN KEY (source_id, admission_id) REFERENCES phase2.admission(source_id, admission_id),
  FOREIGN KEY (source_id, responsible_physician_id) REFERENCES phase2.physician(source_id, physician_id),
  FOREIGN KEY (source_id, hospital_unit_id) REFERENCES phase2.hospital_unit(source_id, hospital_unit_id)
);

CREATE TABLE phase2.surgical_procedure (
  procedure_id integer NOT NULL,
  admission_id integer NOT NULL,
  procedure_type character varying NOT NULL,
  procedure_date date NOT NULL,
  procedure_time time without time zone NOT NULL,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  physician_id integer NOT NULL REFERENCES phase2.physician(physician_id),
  duration_minutes integer NOT NULL CHECK (duration_minutes > 0),
  CONSTRAINT surgical_procedure_pkey PRIMARY KEY (procedure_id),
  CONSTRAINT surgical_procedure_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, procedure_id),
  FOREIGN KEY (source_id, admission_id) REFERENCES phase2.admission(source_id, admission_id),
  FOREIGN KEY (source_id, physician_id) REFERENCES phase2.physician(source_id, physician_id)
);

CREATE TABLE phase2.clinical_note (
  clinical_note_id integer NOT NULL,
  patient_id integer NOT NULL,
  admission_id integer NOT NULL,
  physician_id integer,
  physical_examination text,
  treatment_plan text,
  clinical_findings text,
  diagnostic_examination text,
  medical_condition text,
  symptoms text,
  note_type character varying,
  note_creation_date date,
  note_creation_time time without time zone,
  note_contents text,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  CONSTRAINT clinical_note_pkey PRIMARY KEY (clinical_note_id),
  CONSTRAINT clinical_note_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id),
  CONSTRAINT clinical_note_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id),
  CONSTRAINT clinical_note_physician_id_fkey FOREIGN KEY (physician_id) REFERENCES phase2.physician(physician_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, clinical_note_id),
  FOREIGN KEY (source_id, patient_id) REFERENCES phase2.patient(source_id, patient_id),
  FOREIGN KEY (source_id, admission_id) REFERENCES phase2.admission(source_id, admission_id),
  FOREIGN KEY (source_id, physician_id) REFERENCES phase2.physician(source_id, physician_id)
);

CREATE TABLE phase2.assessment (
  assessment_id integer NOT NULL,
  admission_id integer NOT NULL,
  nurse_id integer,
  blood_pressure character varying,
  heart_rate integer,
  respiratory_rate integer,
  body_temperature numeric,
  oxygen_saturation numeric,
  pain_level integer,
  triage_priority_level integer NOT NULL CHECK (triage_priority_level BETWEEN 1 AND 5),
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  assessment_date date NOT NULL,
  assessment_time time without time zone NOT NULL,
  patient_id integer NOT NULL REFERENCES phase2.patient(patient_id),
  temperature_unit character(1) CHECK (temperature_unit = 'C'),
  CONSTRAINT assessment_pkey PRIMARY KEY (assessment_id),
  CONSTRAINT assessment_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id),
  CONSTRAINT assessment_nurse_id_fkey FOREIGN KEY (nurse_id) REFERENCES phase2.nurse(nurse_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, assessment_id),
  FOREIGN KEY (source_id, admission_id) REFERENCES phase2.admission(source_id, admission_id),
  FOREIGN KEY (source_id, nurse_id) REFERENCES phase2.nurse(source_id, nurse_id),
  FOREIGN KEY (source_id, patient_id) REFERENCES phase2.patient(source_id, patient_id)
);

CREATE TABLE phase2.primary_diagnosis (
  diagnosis_id integer NOT NULL,
  icd9_code character varying NOT NULL,
  diagnosis_date date NOT NULL,
  patient_id integer NOT NULL,
  diagnosis_time time without time zone NOT NULL,
  admission_id integer NOT NULL,
  CONSTRAINT primary_diagnosis_pkey PRIMARY KEY (diagnosis_id),
  CONSTRAINT primary_diagnosis_diagnosis_id_fkey FOREIGN KEY (diagnosis_id) REFERENCES phase2.diagnosis(diagnosis_id),
  CONSTRAINT primary_diagnosis_icd9_code_fkey FOREIGN KEY (icd9_code) REFERENCES phase2.icd9_dictionary(icd9_code),
  CONSTRAINT primary_diagnosis_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id),
  CONSTRAINT primary_diagnosis_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id)
);

CREATE TABLE phase2.secondary_diagnosis (
  diagnosis_id integer NOT NULL,
  icd9_code character varying NOT NULL,
  diagnosis_date date NOT NULL,
  patient_id integer NOT NULL,
  diagnosis_time time without time zone NOT NULL,
  admission_id integer NOT NULL,
  CONSTRAINT secondary_diagnosis_pkey PRIMARY KEY (diagnosis_id),
  CONSTRAINT secondary_diagnosis_diagnosis_id_fkey FOREIGN KEY (diagnosis_id) REFERENCES phase2.diagnosis(diagnosis_id),
  CONSTRAINT secondary_diagnosis_icd9_code_fkey FOREIGN KEY (icd9_code) REFERENCES phase2.icd9_dictionary(icd9_code),
  CONSTRAINT secondary_diagnosis_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id),
  CONSTRAINT secondary_diagnosis_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id)
);

CREATE TABLE phase2.diagnostic_examination (
  examination_id integer NOT NULL,
  diagnostic_order_id integer NOT NULL,
  examination_status character varying NOT NULL,
  examination_time time without time zone NOT NULL,
  examination_date date NOT NULL,
  link_to_images text,
  examination_type character varying NOT NULL,
  radiology_technician character varying,
  body_area_examined character varying,
  referring_physician_id integer,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  admission_id integer NOT NULL REFERENCES phase2.admission(admission_id),
  result_value numeric,
  result_unit text,
  CONSTRAINT diagnostic_examination_pkey PRIMARY KEY (examination_id),
  CONSTRAINT diagnostic_examination_diagnostic_order_id_fkey FOREIGN KEY (diagnostic_order_id) REFERENCES phase2.diagnostic_order(diagnostic_order_id),
  CONSTRAINT diagnostic_examination_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES phase2.physician(physician_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, examination_id),
  FOREIGN KEY (source_id, diagnostic_order_id) REFERENCES phase2.diagnostic_order(source_id, diagnostic_order_id),
  FOREIGN KEY (source_id, referring_physician_id) REFERENCES phase2.physician(source_id, physician_id),
  FOREIGN KEY (source_id, admission_id) REFERENCES phase2.admission(source_id, admission_id)
);

CREATE TABLE phase2.assessment_reported_symptoms (
  assessment_id integer NOT NULL,
  reported_symptom character varying NOT NULL,
  patient_id integer NOT NULL,
  CONSTRAINT assessment_reported_symptoms_pkey PRIMARY KEY (assessment_id, reported_symptom),
  CONSTRAINT assessment_reported_symptoms_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES phase2.assessment(assessment_id),
  CONSTRAINT assessment_reported_symptoms_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id)
);

CREATE TABLE phase2.assessment_known_allergies (
  assessment_id integer NOT NULL,
  known_allergy character varying NOT NULL,
  patient_id integer NOT NULL,
  CONSTRAINT assessment_known_allergies_pkey PRIMARY KEY (assessment_id, known_allergy),
  CONSTRAINT assessment_known_allergies_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES phase2.assessment(assessment_id),
  CONSTRAINT assessment_known_allergies_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id)
);

CREATE TABLE phase2.current_meds (
  current_id integer NOT NULL,
  med_id integer,
  assessment_id integer,
  patient_id integer,
  CONSTRAINT current_meds_pkey PRIMARY KEY (current_id),
  CONSTRAINT current_meds_med_id_fkey FOREIGN KEY (med_id) REFERENCES phase2.medication(medication_id),
  CONSTRAINT current_meds_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES phase2.assessment(assessment_id),
  CONSTRAINT current_meds_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id)
);

CREATE TABLE phase2.blood_test (
  examination_id integer NOT NULL,
  examination_status character varying NOT NULL,
  examination_time time without time zone NOT NULL,
  examination_date date NOT NULL,
  body_area_examined character varying,
  referring_physician_id integer,
  CONSTRAINT blood_test_pkey PRIMARY KEY (examination_id),
  CONSTRAINT blood_test_examination_id_fkey FOREIGN KEY (examination_id) REFERENCES phase2.diagnostic_examination(examination_id),
  CONSTRAINT blood_test_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES phase2.physician(physician_id)
);

CREATE TABLE phase2.ct_examination (
  examination_id integer NOT NULL,
  examination_status character varying NOT NULL,
  examination_time time without time zone NOT NULL,
  examination_date date NOT NULL,
  body_area_examined character varying,
  referring_physician_id integer,
  CONSTRAINT CT_Examination_pkey PRIMARY KEY (examination_id),
  CONSTRAINT CT_Examination_examination_id_fkey FOREIGN KEY (examination_id) REFERENCES phase2.diagnostic_examination(examination_id),
  CONSTRAINT CT_Examination_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES phase2.physician(physician_id)
);

CREATE TABLE phase2.electrodiagram (
  examination_id integer NOT NULL,
  examination_status character varying NOT NULL,
  examination_time time without time zone NOT NULL,
  examination_date date NOT NULL,
  body_area_examined character varying,
  referring_physician_id integer,
  CONSTRAINT electrodiagram_pkey PRIMARY KEY (examination_id),
  CONSTRAINT electrodiagram_examination_id_fkey FOREIGN KEY (examination_id) REFERENCES phase2.diagnostic_examination(examination_id),
  CONSTRAINT electrodiagram_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES phase2.physician(physician_id)
);

CREATE TABLE phase2.radiology_examination (
  examination_id integer NOT NULL,
  admission_id integer,
  reviewed_by_radiologist_id integer,
  examination_status character varying NOT NULL,
  examination_time time without time zone NOT NULL,
  examination_date date NOT NULL,
  link_to_images text,
  examination_type character varying NOT NULL,
  radiology_technician character varying,
  body_area_examined character varying,
  referring_physician_id integer,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  CONSTRAINT radiology_examination_pkey PRIMARY KEY (examination_id),
  CONSTRAINT radiology_examination_examination_id_fkey FOREIGN KEY (examination_id) REFERENCES phase2.diagnostic_examination(examination_id),
  CONSTRAINT radiology_examination_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id),
  CONSTRAINT radiology_examination_reviewed_by_radiologist_id_fkey FOREIGN KEY (reviewed_by_radiologist_id) REFERENCES phase2.radiologist(radiologist_id),
  CONSTRAINT radiology_examination_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES phase2.physician(physician_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, examination_id),
  FOREIGN KEY (source_id, examination_id) REFERENCES phase2.diagnostic_examination(source_id, examination_id),
  FOREIGN KEY (source_id, admission_id) REFERENCES phase2.admission(source_id, admission_id),
  FOREIGN KEY (source_id, reviewed_by_radiologist_id) REFERENCES phase2.radiologist(source_id, radiologist_id),
  FOREIGN KEY (source_id, referring_physician_id) REFERENCES phase2.physician(source_id, physician_id)
);

CREATE TABLE phase2.discharge_record (
  discharge_record_id integer NOT NULL,
  admission_id integer NOT NULL UNIQUE,
  discharge_date date NOT NULL,
  discharge_time time without time zone NOT NULL,
  discharge_destination character varying NOT NULL,
  patient_condition character varying NOT NULL,
  primary_diagnosis_id integer NOT NULL,
  follow_up_instructions text,
  scheduled_follow_up_appointment date,
  responsible_physician_id integer,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  responsible_physician_name text,
  CONSTRAINT discharge_record_pkey PRIMARY KEY (discharge_record_id),
  CONSTRAINT discharge_record_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES phase2.admission(admission_id),
  CONSTRAINT discharge_record_primary_diagnosis_id_fkey FOREIGN KEY (primary_diagnosis_id) REFERENCES phase2.primary_diagnosis(diagnosis_id),
  CONSTRAINT discharge_record_responsible_physician_id_fkey FOREIGN KEY (responsible_physician_id) REFERENCES phase2.physician(physician_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, discharge_record_id),
  FOREIGN KEY (source_id, admission_id) REFERENCES phase2.admission(source_id, admission_id),
  FOREIGN KEY (source_id, responsible_physician_id) REFERENCES phase2.physician(source_id, physician_id)
);

CREATE TABLE phase2.radiology_report (
  radiology_report_id integer NOT NULL,
  radiologist_id integer NOT NULL,
  findings text NOT NULL,
  interpretation text NOT NULL,
  clinical_conclusion text NOT NULL,
  radiology_examination_id integer NOT NULL,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  report_date date NOT NULL,
  report_time time without time zone NOT NULL,
  CONSTRAINT radiology_report_pkey PRIMARY KEY (radiology_report_id),
  CONSTRAINT radiology_report_radiologist_id_fkey FOREIGN KEY (radiologist_id) REFERENCES phase2.radiologist(radiologist_id),
  CONSTRAINT radiology_report_examination_fkey FOREIGN KEY (radiology_examination_id) REFERENCES phase2.radiology_examination(examination_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, radiology_report_id),
  FOREIGN KEY (source_id, radiologist_id) REFERENCES phase2.radiologist(source_id, radiologist_id),
  FOREIGN KEY (source_id, radiology_examination_id) REFERENCES phase2.radiology_examination(source_id, examination_id)
);

CREATE TABLE phase2.discharge_record_secondary_diagnosis (
  discharge_record_id integer NOT NULL,
  secondary_diagnosis_id integer NOT NULL,
  CONSTRAINT discharge_record_secondary_diagnosis_pkey PRIMARY KEY (discharge_record_id, secondary_diagnosis_id),
  CONSTRAINT discharge_record_secondary_diagnosis_discharge_record_id_fkey FOREIGN KEY (discharge_record_id) REFERENCES phase2.discharge_record(discharge_record_id),
  CONSTRAINT discharge_record_secondary_diagnosi_secondary_diagnosis_id_fkey FOREIGN KEY (secondary_diagnosis_id) REFERENCES phase2.secondary_diagnosis(diagnosis_id)
);

CREATE TABLE phase2.discharge_summary (
  discharge_summary_id integer NOT NULL,
  discharge_record_id integer NOT NULL UNIQUE,
  responsible_physician_id integer,
  admission_reason text NOT NULL,
  examination_results text,
  treatments_provided text,
  unit_transfers text,
  icd9_coded_diagnoses text,
  recommendations text,
  source_id character(1) NOT NULL REFERENCES phase2.source_system(source_id),
  original_id integer NOT NULL CHECK (original_id > 0),
  CONSTRAINT discharge_summary_pkey PRIMARY KEY (discharge_summary_id),
  CONSTRAINT discharge_summary_discharge_record_id_fkey FOREIGN KEY (discharge_record_id) REFERENCES phase2.discharge_record(discharge_record_id),
  CONSTRAINT discharge_summary_responsible_physician_id_fkey FOREIGN KEY (responsible_physician_id) REFERENCES phase2.physician(physician_id),
  UNIQUE (source_id, original_id),
  UNIQUE (source_id, discharge_summary_id),
  FOREIGN KEY (source_id, discharge_record_id) REFERENCES phase2.discharge_record(source_id, discharge_record_id),
  FOREIGN KEY (source_id, responsible_physician_id) REFERENCES phase2.physician(source_id, physician_id)
);

CREATE TABLE phase2.discharge_record_primary_diagnosis (
  discharge_record_id integer NOT NULL,
  primary_diagnosis_id integer NOT NULL,
  CONSTRAINT discharge_record_primary_diagnosis_pkey PRIMARY KEY (discharge_record_id, primary_diagnosis_id),
  CONSTRAINT discharge_record_primary_diagnosis_discharge_record_id_fkey FOREIGN KEY (discharge_record_id) REFERENCES phase2.discharge_record(discharge_record_id),
  CONSTRAINT discharge_record_primary_diagnosis_primary_diagnosis_id_fkey FOREIGN KEY (primary_diagnosis_id) REFERENCES phase2.primary_diagnosis(diagnosis_id)
);

CREATE TABLE phase2.prescribed_meds (
  prescribed_id integer NOT NULL,
  med_id integer,
  prescribed_to_id integer,
  patient_id integer,
  CONSTRAINT prescribed_meds_pkey PRIMARY KEY (prescribed_id),
  CONSTRAINT prescribed_meds_med_id_fkey FOREIGN KEY (med_id) REFERENCES phase2.medication(medication_id),
  CONSTRAINT prescribed_meds_prescribed_to_id_fkey FOREIGN KEY (prescribed_to_id) REFERENCES phase2.discharge_record(discharge_record_id),
  CONSTRAINT prescribed_meds_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES phase2.patient(patient_id)
);

-- Source labels identify fictional hospital systems, not real institutions.
INSERT INTO phase2.source_system (source_id, hospital_name, country, continent, file_format) VALUES
  ('A', 'Synthetic Hospital A', 'Canada', 'North America', 'TXT'),
  ('B', 'Synthetic Hospital B', 'Germany', 'Europe', 'CSV'),
  ('C', 'Synthetic Hospital C', 'Japan', 'Asia', 'XML'),
  ('D', 'Synthetic Hospital D', 'South Africa', 'Africa', 'JSON');
COMMIT;
