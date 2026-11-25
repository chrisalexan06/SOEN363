
CREATE TABLE public.icd9_dictionary (
  icd9_code character varying NOT NULL,
  diagnosis_title character varying NOT NULL,
  description text NOT NULL,
  disease_category character varying NOT NULL,
  CONSTRAINT icd9_dictionary_pkey PRIMARY KEY (icd9_code)
);
CREATE TABLE public.patient (
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
  CONSTRAINT patient_pkey PRIMARY KEY (patient_id),
  CONSTRAINT patient_physician_id_fkey FOREIGN KEY (physician_id) REFERENCES public.physician(physician_id),
  CONSTRAINT patient_nurse_id_fkey FOREIGN KEY (nurse_id) REFERENCES public.nurse(nurse_id)
);
CREATE TABLE public.physician (
  physician_id integer NOT NULL,
  physician_name character varying NOT NULL,
  CONSTRAINT physician_pkey PRIMARY KEY (physician_id)
);
CREATE TABLE public.nurse (
  nurse_id integer NOT NULL,
  nurse_name character varying NOT NULL,
  CONSTRAINT nurse_pkey PRIMARY KEY (nurse_id)
);
CREATE TABLE public.radiologist (
  radiologist_id integer NOT NULL,
  radiologist_name character varying NOT NULL,
  CONSTRAINT radiologist_pkey PRIMARY KEY (radiologist_id)
);
CREATE TABLE public.admission (
  admission_id integer NOT NULL DEFAULT nextval('admission_admission_id_seq'::regclass),
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
  CONSTRAINT admission_pkey PRIMARY KEY (admission_id),
  CONSTRAINT admission_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id),
  CONSTRAINT admission_nurse_id_fkey FOREIGN KEY (nurse_id) REFERENCES public.nurse(nurse_id),
  CONSTRAINT fk_past_record_followup FOREIGN KEY (past_record_followup) REFERENCES public.admission(admission_id)
);
CREATE TABLE public.diagnosis (
  diagnosis_id integer NOT NULL DEFAULT nextval('diagnosis_diagnosis_id_seq'::regclass),
  icd9_code character varying NOT NULL,
  diagnosis_date date NOT NULL,
  diagnosis_time time without time zone NOT NULL,
  diagnosis_type character varying NOT NULL,
  patient_id integer NOT NULL,
  admission_id integer NOT NULL,
  physician_id integer NOT NULL,
  CONSTRAINT diagnosis_pkey PRIMARY KEY (diagnosis_id),
  CONSTRAINT diagnosis_icd9_code_fkey FOREIGN KEY (icd9_code) REFERENCES public.icd9_dictionary(icd9_code),
  CONSTRAINT diagnosis_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id),
  CONSTRAINT diagnosis_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id),
  CONSTRAINT diagnosis_physician_id_fkey FOREIGN KEY (physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.primary_diagnosis (
  diagnosis_id integer NOT NULL,
  icd9_code character varying NOT NULL,
  diagnosis_date date NOT NULL,
  patient_id integer NOT NULL,
  diagnosis_time time without time zone NOT NULL,
  admission_id integer NOT NULL,
  CONSTRAINT primary_diagnosis_pkey PRIMARY KEY (diagnosis_id),
  CONSTRAINT primary_diagnosis_diagnosis_id_fkey FOREIGN KEY (diagnosis_id) REFERENCES public.diagnosis(diagnosis_id),
  CONSTRAINT primary_diagnosis_icd9_code_fkey FOREIGN KEY (icd9_code) REFERENCES public.icd9_dictionary(icd9_code),
  CONSTRAINT primary_diagnosis_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id),
  CONSTRAINT primary_diagnosis_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id)
);
CREATE TABLE public.secondary_diagnosis (
  diagnosis_id integer NOT NULL,
  icd9_code character varying NOT NULL,
  diagnosis_date date NOT NULL,
  patient_id integer NOT NULL,
  diagnosis_time time without time zone NOT NULL,
  admission_id integer NOT NULL,
  CONSTRAINT secondary_diagnosis_pkey PRIMARY KEY (diagnosis_id),
  CONSTRAINT secondary_diagnosis_diagnosis_id_fkey FOREIGN KEY (diagnosis_id) REFERENCES public.diagnosis(diagnosis_id),
  CONSTRAINT secondary_diagnosis_icd9_code_fkey FOREIGN KEY (icd9_code) REFERENCES public.icd9_dictionary(icd9_code),
  CONSTRAINT secondary_diagnosis_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id),
  CONSTRAINT secondary_diagnosis_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id)
);
CREATE TABLE public.diagnostic_order (
  diagnostic_order_id integer NOT NULL DEFAULT nextval('diagnostic_order_diagnostic_order_id_seq'::regclass),
  patient_id integer NOT NULL,
  admission_id integer NOT NULL,
  requesting_physician integer NOT NULL,
  requested_examination character varying NOT NULL,
  request_date date NOT NULL,
  request_time time without time zone NOT NULL,
  clinical_reason text NOT NULL,
  priority character varying NOT NULL,
  order_status character varying NOT NULL,
  CONSTRAINT diagnostic_order_pkey PRIMARY KEY (diagnostic_order_id),
  CONSTRAINT diagnostic_order_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id),
  CONSTRAINT diagnostic_order_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id),
  CONSTRAINT diagnostic_order_requesting_physician_fkey FOREIGN KEY (requesting_physician) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.diagnostic_examination (
  examination_id integer NOT NULL DEFAULT nextval('diagnostic_examination_examination_id_seq'::regclass),
  diagnostic_order_id integer NOT NULL,
  examination_status character varying NOT NULL,
  examination_time time without time zone NOT NULL,
  examination_date date NOT NULL,
  link_to_images text,
  examination_type character varying NOT NULL,
  radiology_technician character varying,
  body_area_examined character varying,
  referring_physician_id integer,
  CONSTRAINT diagnostic_examination_pkey PRIMARY KEY (examination_id),
  CONSTRAINT diagnostic_examination_diagnostic_order_id_fkey FOREIGN KEY (diagnostic_order_id) REFERENCES public.diagnostic_order(diagnostic_order_id),
  CONSTRAINT diagnostic_examination_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.blood_test (
  examination_id integer NOT NULL,
  examination_status character varying NOT NULL,
  examination_time time without time zone NOT NULL,
  examination_date date NOT NULL,
  body_area_examined character varying,
  referring_physician_id integer,
  CONSTRAINT blood_test_pkey PRIMARY KEY (examination_id),
  CONSTRAINT blood_test_examination_id_fkey FOREIGN KEY (examination_id) REFERENCES public.diagnostic_examination(examination_id),
  CONSTRAINT blood_test_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.CT_Examination (
  examination_id integer NOT NULL,
  examination_status character varying NOT NULL,
  examination_time time without time zone NOT NULL,
  examination_date date NOT NULL,
  body_area_examined character varying,
  referring_physician_id integer,
  CONSTRAINT CT_Examination_pkey PRIMARY KEY (examination_id),
  CONSTRAINT CT_Examination_examination_id_fkey FOREIGN KEY (examination_id) REFERENCES public.diagnostic_examination(examination_id),
  CONSTRAINT CT_Examination_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.electrodiagram (
  examination_id integer NOT NULL,
  examination_status character varying NOT NULL,
  examination_time time without time zone NOT NULL,
  examination_date date NOT NULL,
  body_area_examined character varying,
  referring_physician_id integer,
  CONSTRAINT electrodiagram_pkey PRIMARY KEY (examination_id),
  CONSTRAINT electrodiagram_examination_id_fkey FOREIGN KEY (examination_id) REFERENCES public.diagnostic_examination(examination_id),
  CONSTRAINT electrodiagram_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.radiology_examination (
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
  CONSTRAINT radiology_examination_pkey PRIMARY KEY (examination_id),
  CONSTRAINT radiology_examination_examination_id_fkey FOREIGN KEY (examination_id) REFERENCES public.diagnostic_examination(examination_id),
  CONSTRAINT radiology_examination_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id),
  CONSTRAINT radiology_examination_reviewed_by_radiologist_id_fkey FOREIGN KEY (reviewed_by_radiologist_id) REFERENCES public.radiologist(radiologist_id),
  CONSTRAINT radiology_examination_referring_physician_id_fkey FOREIGN KEY (referring_physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.radiology_report (
  radiology_report_id integer NOT NULL DEFAULT nextval('radiology_report_radiology_report_id_seq'::regclass),
  radiologist_id integer NOT NULL,
  findings text NOT NULL,
  interpretation text NOT NULL,
  clinical_conclusion text NOT NULL,
  radiology_examination_id integer,
  CONSTRAINT radiology_report_pkey PRIMARY KEY (radiology_report_id),
  CONSTRAINT radiology_report_radiologist_id_fkey FOREIGN KEY (radiologist_id) REFERENCES public.radiologist(radiologist_id),
  CONSTRAINT radiology_report_examination_fkey FOREIGN KEY (radiology_examination_id) REFERENCES public.radiology_examination(examination_id)
);
CREATE TABLE public.unit_stay (
  unit_stay_id integer NOT NULL DEFAULT nextval('unit_stay_unit_stay_id_seq'::regclass),
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
  CONSTRAINT unit_stay_pkey PRIMARY KEY (unit_stay_id),
  CONSTRAINT unit_stay_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id),
  CONSTRAINT unit_stay_responsible_physician_id_fkey FOREIGN KEY (responsible_physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.surgical_procedure (
  procedure_id integer NOT NULL DEFAULT nextval('surgical_procedure_procedure_id_seq'::regclass),
  admission_id integer NOT NULL,
  procedure_type character varying NOT NULL,
  procedure_date date NOT NULL,
  procedure_time time without time zone NOT NULL,
  CONSTRAINT surgical_procedure_pkey PRIMARY KEY (procedure_id),
  CONSTRAINT surgical_procedure_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id)
);
CREATE TABLE public.clinical_note (
  clinical_note_id integer NOT NULL DEFAULT nextval('clinical_note_clinical_note_id_seq'::regclass),
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
  CONSTRAINT clinical_note_pkey PRIMARY KEY (clinical_note_id),
  CONSTRAINT clinical_note_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id),
  CONSTRAINT clinical_note_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id),
  CONSTRAINT clinical_note_physician_id_fkey FOREIGN KEY (physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.assessment (
  assessment_id integer NOT NULL DEFAULT nextval('assessment_assessment_id_seq'::regclass),
  admission_id integer NOT NULL,
  nurse_id integer,
  blood_pressure character varying,
  heart_rate integer,
  respiratory_rate integer,
  body_temperature numeric,
  oxygen_saturation numeric,
  pain_level integer,
  triage_priority_level character varying NOT NULL,
  CONSTRAINT assessment_pkey PRIMARY KEY (assessment_id),
  CONSTRAINT assessment_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id),
  CONSTRAINT assessment_nurse_id_fkey FOREIGN KEY (nurse_id) REFERENCES public.nurse(nurse_id)
);
CREATE TABLE public.assessment_reported_symptoms (
  assessment_id integer NOT NULL,
  reported_symptom character varying NOT NULL,
  patient_id integer NOT NULL,
  CONSTRAINT assessment_reported_symptoms_pkey PRIMARY KEY (assessment_id, reported_symptom),
  CONSTRAINT assessment_reported_symptoms_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.assessment(assessment_id),
  CONSTRAINT assessment_reported_symptoms_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id)
);
CREATE TABLE public.assessment_known_allergies (
  assessment_id integer NOT NULL,
  known_allergy character varying NOT NULL,
  patient_id integer NOT NULL,
  CONSTRAINT assessment_known_allergies_pkey PRIMARY KEY (assessment_id, known_allergy),
  CONSTRAINT assessment_known_allergies_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.assessment(assessment_id),
  CONSTRAINT assessment_known_allergies_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id)
);
CREATE TABLE public.discharge_record (
  discharge_record_id integer NOT NULL DEFAULT nextval('discharge_record_discharge_record_id_seq'::regclass),
  admission_id integer NOT NULL UNIQUE,
  discharge_date date NOT NULL,
  discharge_time time without time zone NOT NULL,
  discharge_destination character varying NOT NULL,
  patient_condition character varying NOT NULL,
  primary_diagnosis_id integer NOT NULL,
  follow_up_instructions text,
  scheduled_follow_up_appointment date,
  responsible_physician_id integer,
  CONSTRAINT discharge_record_pkey PRIMARY KEY (discharge_record_id),
  CONSTRAINT discharge_record_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admission(admission_id),
  CONSTRAINT discharge_record_primary_diagnosis_id_fkey FOREIGN KEY (primary_diagnosis_id) REFERENCES public.primary_diagnosis(diagnosis_id),
  CONSTRAINT discharge_record_responsible_physician_id_fkey FOREIGN KEY (responsible_physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.discharge_record_secondary_diagnosis (
  discharge_record_id integer NOT NULL,
  secondary_diagnosis_id integer NOT NULL,
  CONSTRAINT discharge_record_secondary_diagnosis_pkey PRIMARY KEY (discharge_record_id, secondary_diagnosis_id),
  CONSTRAINT discharge_record_secondary_diagnosis_discharge_record_id_fkey FOREIGN KEY (discharge_record_id) REFERENCES public.discharge_record(discharge_record_id),
  CONSTRAINT discharge_record_secondary_diagnosi_secondary_diagnosis_id_fkey FOREIGN KEY (secondary_diagnosis_id) REFERENCES public.secondary_diagnosis(diagnosis_id)
);
CREATE TABLE public.discharge_summary (
  discharge_summary_id integer NOT NULL DEFAULT nextval('discharge_summary_discharge_summary_id_seq'::regclass),
  discharge_record_id integer NOT NULL UNIQUE,
  responsible_physician_id integer,
  admission_reason text NOT NULL,
  examination_results text,
  treatments_provided text,
  unit_transfers text,
  icd9_coded_diagnoses text,
  recommendations text,
  CONSTRAINT discharge_summary_pkey PRIMARY KEY (discharge_summary_id),
  CONSTRAINT discharge_summary_discharge_record_id_fkey FOREIGN KEY (discharge_record_id) REFERENCES public.discharge_record(discharge_record_id),
  CONSTRAINT discharge_summary_responsible_physician_id_fkey FOREIGN KEY (responsible_physician_id) REFERENCES public.physician(physician_id)
);
CREATE TABLE public.discharge_record_primary_diagnosis (
  discharge_record_id integer NOT NULL,
  primary_diagnosis_id integer NOT NULL,
  CONSTRAINT discharge_record_primary_diagnosis_pkey PRIMARY KEY (discharge_record_id, primary_diagnosis_id),
  CONSTRAINT discharge_record_primary_diagnosis_discharge_record_id_fkey FOREIGN KEY (discharge_record_id) REFERENCES public.discharge_record(discharge_record_id),
  CONSTRAINT discharge_record_primary_diagnosis_primary_diagnosis_id_fkey FOREIGN KEY (primary_diagnosis_id) REFERENCES public.primary_diagnosis(diagnosis_id)
);
CREATE TABLE public.medication (
  medication_id integer NOT NULL,
  medication_name character varying,
  CONSTRAINT medication_pkey PRIMARY KEY (medication_id)
);
CREATE TABLE public.current_meds (
  current_id integer NOT NULL,
  med_id integer,
  assessment_id integer,
  patient_id integer,
  CONSTRAINT current_meds_pkey PRIMARY KEY (current_id),
  CONSTRAINT current_meds_med_id_fkey FOREIGN KEY (med_id) REFERENCES public.medication(medication_id),
  CONSTRAINT current_meds_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.assessment(assessment_id),
  CONSTRAINT current_meds_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id)
);
CREATE TABLE public.prescribed_meds (
  prescribed_id integer NOT NULL,
  med_id integer,
  prescribed_to_id integer,
  patient_id integer,
  CONSTRAINT prescribed_meds_pkey PRIMARY KEY (prescribed_id),
  CONSTRAINT prescribed_meds_med_id_fkey FOREIGN KEY (med_id) REFERENCES public.medication(medication_id),
  CONSTRAINT prescribed_meds_prescribed_to_id_fkey FOREIGN KEY (prescribed_to_id) REFERENCES public.discharge_record(discharge_record_id),
  CONSTRAINT prescribed_meds_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient(patient_id)
);