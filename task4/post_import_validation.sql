-- Read-only post-import validation for the phase2 schema.
-- Run each SELECT in the Supabase SQL Editor after import_data.py completes.
-- Constraint metadata confirms that primary/foreign/check constraints exist
-- and are validated; row-level checks report any remaining data violations.

-- 1. Confirm every phase2 table has a validated primary key.
SELECT
  COUNT(*) AS phase2_table_count,
  COUNT(*) FILTER (
    WHERE EXISTS (
      SELECT 1
      FROM pg_constraint con
      WHERE con.conrelid = to_regclass(format('%I.%I', t.schemaname, t.tablename))
        AND con.contype = 'p'
        AND con.convalidated
    )
  ) AS tables_with_validated_primary_key,
  COUNT(*) FILTER (
    WHERE NOT EXISTS (
      SELECT 1
      FROM pg_constraint con
      WHERE con.conrelid = to_regclass(format('%I.%I', t.schemaname, t.tablename))
        AND con.contype = 'p'
        AND con.convalidated
    )
  ) AS tables_missing_validated_primary_key
FROM pg_tables t
WHERE t.schemaname = 'phase2';

-- 2. Inspect primary, foreign-key, and check constraints and their validation state.
SELECT
  con.contype AS constraint_type,
  COUNT(*) AS constraint_count,
  COUNT(*) FILTER (WHERE con.convalidated) AS validated_count,
  COUNT(*) FILTER (WHERE NOT con.convalidated) AS not_validated_count
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace ns ON ns.oid = rel.relnamespace
WHERE ns.nspname = 'phase2'
  AND con.contype IN ('p', 'f', 'c')
GROUP BY con.contype
ORDER BY con.contype;

-- 3. List required columns so NOT NULL coverage can be reviewed against the
-- documented data rules.
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = 'phase2'
  AND is_nullable = 'NO'
ORDER BY table_name, ordinal_position;

-- 4. Row-level integrity checks. Each violation_count should be zero.
WITH checks AS (
  SELECT
    'admissions_without_patient' AS check_name,
    COUNT(*)::bigint AS violation_count
  FROM phase2.admission a
  LEFT JOIN phase2.patient p ON p.patient_id = a.patient_id
  WHERE p.patient_id IS NULL

  UNION ALL
  SELECT
    'diagnoses_without_admission_or_icd9',
    COUNT(*)::bigint
  FROM phase2.diagnosis d
  LEFT JOIN phase2.admission a ON a.admission_id = d.admission_id
  LEFT JOIN phase2.icd9_dictionary i ON i.icd9_code = d.icd9_code
  WHERE a.admission_id IS NULL OR i.icd9_code IS NULL

  UNION ALL
  SELECT
    'patient_admission_identity_mismatches',
    COUNT(*)::bigint
  FROM (
    SELECT d.patient_id, d.admission_id
    FROM phase2.diagnosis d
    LEFT JOIN phase2.admission a ON a.admission_id = d.admission_id
    WHERE a.admission_id IS NULL OR d.patient_id IS DISTINCT FROM a.patient_id
    UNION ALL
    SELECT o.patient_id, o.admission_id
    FROM phase2.diagnostic_order o
    LEFT JOIN phase2.admission a ON a.admission_id = o.admission_id
    WHERE a.admission_id IS NULL OR o.patient_id IS DISTINCT FROM a.patient_id
    UNION ALL
    SELECT n.patient_id, n.admission_id
    FROM phase2.clinical_note n
    LEFT JOIN phase2.admission a ON a.admission_id = n.admission_id
    WHERE a.admission_id IS NULL OR n.patient_id IS DISTINCT FROM a.patient_id
    UNION ALL
    SELECT x.patient_id, x.admission_id
    FROM phase2.assessment x
    LEFT JOIN phase2.admission a ON a.admission_id = x.admission_id
    WHERE a.admission_id IS NULL OR x.patient_id IS DISTINCT FROM a.patient_id
    UNION ALL
    SELECT p.patient_id, p.admission_id
    FROM phase2.primary_diagnosis p
    LEFT JOIN phase2.admission a ON a.admission_id = p.admission_id
    WHERE a.admission_id IS NULL OR p.patient_id IS DISTINCT FROM a.patient_id
    UNION ALL
    SELECT s.patient_id, s.admission_id
    FROM phase2.secondary_diagnosis s
    LEFT JOIN phase2.admission a ON a.admission_id = s.admission_id
    WHERE a.admission_id IS NULL OR s.patient_id IS DISTINCT FROM a.patient_id
  ) mismatches

  UNION ALL
  SELECT
    'diagnosis_subtype_identity_mismatches',
    COUNT(*)::bigint
  FROM (
    SELECT p.diagnosis_id
    FROM phase2.primary_diagnosis p
    LEFT JOIN phase2.diagnosis d ON d.diagnosis_id = p.diagnosis_id
    WHERE d.diagnosis_id IS NULL
       OR d.diagnosis_type <> 'Primary'
       OR p.icd9_code IS DISTINCT FROM d.icd9_code
       OR p.patient_id IS DISTINCT FROM d.patient_id
       OR p.admission_id IS DISTINCT FROM d.admission_id
    UNION ALL
    SELECT s.diagnosis_id
    FROM phase2.secondary_diagnosis s
    LEFT JOIN phase2.diagnosis d ON d.diagnosis_id = s.diagnosis_id
    WHERE d.diagnosis_id IS NULL
       OR d.diagnosis_type <> 'Secondary'
       OR s.icd9_code IS DISTINCT FROM d.icd9_code
       OR s.patient_id IS DISTINCT FROM d.patient_id
       OR s.admission_id IS DISTINCT FROM d.admission_id
  ) mismatches

  UNION ALL
  SELECT
    'diagnostic_examination_order_admission_mismatches',
    COUNT(*)::bigint
  FROM phase2.diagnostic_examination e
  LEFT JOIN phase2.diagnostic_order o
    ON o.diagnostic_order_id = e.diagnostic_order_id
  WHERE o.diagnostic_order_id IS NULL
     OR e.admission_id IS DISTINCT FROM o.admission_id

  UNION ALL
  SELECT
    'radiology_examination_parent_mismatches',
    COUNT(*)::bigint
  FROM phase2.radiology_examination r
  LEFT JOIN phase2.diagnostic_examination e
    ON e.examination_id = r.examination_id
  WHERE e.examination_id IS NULL
     OR r.admission_id IS DISTINCT FROM e.admission_id
     OR r.examination_date IS DISTINCT FROM e.examination_date
     OR r.examination_time IS DISTINCT FROM e.examination_time

  UNION ALL
  SELECT
    'discharge_primary_diagnosis_admission_mismatches',
    COUNT(*)::bigint
  FROM phase2.discharge_record d
  LEFT JOIN phase2.primary_diagnosis p
    ON p.diagnosis_id = d.primary_diagnosis_id
  WHERE p.diagnosis_id IS NULL
     OR p.admission_id IS DISTINCT FROM d.admission_id

  UNION ALL
  SELECT
    'discharge_diagnosis_junction_admission_mismatches',
    COUNT(*)::bigint
  FROM (
    SELECT j.discharge_record_id
    FROM phase2.discharge_record_primary_diagnosis j
    LEFT JOIN phase2.discharge_record d
      ON d.discharge_record_id = j.discharge_record_id
    LEFT JOIN phase2.primary_diagnosis p
      ON p.diagnosis_id = j.primary_diagnosis_id
    WHERE d.discharge_record_id IS NULL
       OR p.diagnosis_id IS NULL
       OR d.admission_id IS DISTINCT FROM p.admission_id
       OR d.primary_diagnosis_id IS DISTINCT FROM p.diagnosis_id
    UNION ALL
    SELECT j.discharge_record_id
    FROM phase2.discharge_record_secondary_diagnosis j
    LEFT JOIN phase2.discharge_record d
      ON d.discharge_record_id = j.discharge_record_id
    LEFT JOIN phase2.secondary_diagnosis s
      ON s.diagnosis_id = j.secondary_diagnosis_id
    WHERE d.discharge_record_id IS NULL
       OR s.diagnosis_id IS NULL
       OR d.admission_id IS DISTINCT FROM s.admission_id
  ) mismatches

  UNION ALL
  SELECT
    'patient_assessment_identity_mismatches',
    COUNT(*)::bigint
  FROM (
    SELECT s.patient_id, s.assessment_id
    FROM phase2.assessment_reported_symptoms s
    LEFT JOIN phase2.assessment a ON a.assessment_id = s.assessment_id
    WHERE a.assessment_id IS NULL OR s.patient_id IS DISTINCT FROM a.patient_id
    UNION ALL
    SELECT k.patient_id, k.assessment_id
    FROM phase2.assessment_known_allergies k
    LEFT JOIN phase2.assessment a ON a.assessment_id = k.assessment_id
    WHERE a.assessment_id IS NULL OR k.patient_id IS DISTINCT FROM a.patient_id
    UNION ALL
    SELECT m.patient_id, m.assessment_id
    FROM phase2.current_meds m
    LEFT JOIN phase2.assessment a ON a.assessment_id = m.assessment_id
    WHERE m.assessment_id IS NOT NULL
      AND m.patient_id IS NOT NULL
      AND (a.assessment_id IS NULL OR m.patient_id IS DISTINCT FROM a.patient_id)
  ) mismatches

  UNION ALL
  SELECT
    'prescription_patient_discharge_mismatches',
    COUNT(*)::bigint
  FROM phase2.prescribed_meds p
  LEFT JOIN phase2.discharge_record d ON d.discharge_record_id = p.prescribed_to_id
  LEFT JOIN phase2.admission a ON a.admission_id = d.admission_id
  WHERE p.prescribed_to_id IS NOT NULL
    AND p.patient_id IS NOT NULL
    AND (a.admission_id IS NULL OR p.patient_id IS DISTINCT FROM a.patient_id)

  UNION ALL
  SELECT
    'admission_status_or_discharge_time_violations',
    COUNT(*)::bigint
  FROM phase2.admission a
  WHERE a.admission_status NOT IN ('Open', 'Closed')
     OR (a.admission_status = 'Open'
         AND (a.discharge_date IS NOT NULL OR a.discharge_time IS NOT NULL))
     OR (a.admission_status = 'Closed'
         AND (a.discharge_date IS NULL OR a.discharge_time IS NULL
              OR a.discharge_date + a.discharge_time
                   <= a.admission_date + a.admission_time))

  UNION ALL
  SELECT
    'unit_stay_interval_or_admission_period_violations',
    COUNT(*)::bigint
  FROM phase2.unit_stay u
  JOIN phase2.admission a ON a.admission_id = u.admission_id
  WHERE (u.exit_date IS NULL) <> (u.exit_time IS NULL)
     OR (u.exit_date IS NOT NULL
         AND u.exit_date + u.exit_time <= u.entry_date + u.entry_time)
     OR u.entry_date + u.entry_time < a.admission_date + a.admission_time
     OR (a.discharge_date IS NOT NULL
         AND (u.entry_date + u.entry_time > a.discharge_date + a.discharge_time
              OR (u.exit_date IS NOT NULL
                  AND u.exit_date + u.exit_time > a.discharge_date + a.discharge_time)))

  UNION ALL
  SELECT
    'diagnostic_examination_period_violations',
    COUNT(*)::bigint
  FROM phase2.diagnostic_examination e
  JOIN phase2.admission a ON a.admission_id = e.admission_id
  WHERE e.examination_date + e.examination_time
          < a.admission_date + a.admission_time
     OR (a.discharge_date IS NOT NULL
         AND e.examination_date + e.examination_time
             > a.discharge_date + a.discharge_time)

  UNION ALL
  SELECT
    'radiology_examination_period_violations',
    COUNT(*)::bigint
  FROM phase2.radiology_examination e
  LEFT JOIN phase2.admission a ON a.admission_id = e.admission_id
  WHERE a.admission_id IS NULL
     OR e.examination_date + e.examination_time
          < a.admission_date + a.admission_time
     OR (a.discharge_date IS NOT NULL
         AND e.examination_date + e.examination_time
             > a.discharge_date + a.discharge_time)

  UNION ALL
  SELECT
    'surgical_procedure_period_violations',
    COUNT(*)::bigint
  FROM phase2.surgical_procedure p
  JOIN phase2.admission a ON a.admission_id = p.admission_id
  WHERE p.procedure_date + p.procedure_time
          < a.admission_date + a.admission_time
     OR (a.discharge_date IS NOT NULL
         AND p.procedure_date + p.procedure_time
             + p.duration_minutes * INTERVAL '1 minute'
             > a.discharge_date + a.discharge_time)

  UNION ALL
  SELECT
    'closed_admissions_without_primary_icd9',
    COUNT(*)::bigint
  FROM phase2.admission a
  WHERE a.admission_status = 'Closed'
    AND NOT EXISTS (
      SELECT 1
      FROM phase2.primary_diagnosis p
      JOIN phase2.icd9_dictionary i ON i.icd9_code = p.icd9_code
      WHERE p.admission_id = a.admission_id
    )

  UNION ALL
  SELECT
    'discharge_record_status_or_timestamp_mismatches',
    COUNT(*)::bigint
  FROM phase2.discharge_record d
  LEFT JOIN phase2.admission a ON a.admission_id = d.admission_id
  WHERE a.admission_id IS NULL
     OR a.admission_status <> 'Closed'
     OR d.discharge_date IS DISTINCT FROM a.discharge_date
     OR d.discharge_time IS DISTINCT FROM a.discharge_time

  UNION ALL
  SELECT
    'documented_category_domain_violations',
    (
      SELECT COUNT(*) FROM phase2.patient p
      WHERE p.life_status NOT IN ('Alive', 'Deceased')
         OR p.gender NOT IN ('Male', 'Female', 'Other')
    )
    + (SELECT COUNT(*) FROM phase2.admission a
       WHERE a.admission_status NOT IN ('Open', 'Closed')
          OR a.admission_type NOT IN ('Emergency', 'Elective')
          OR a.admission_source NOT IN
             ('Emergency Department', 'Hospital Transfer', 'Physician Referral')
          OR a.patient_condition NOT IN
             ('Critical', 'Stable', 'Requires monitoring', 'Recovered',
              'Transferred', 'Improving', 'Deceased'))
    + (SELECT COUNT(*) FROM phase2.diagnosis d
       WHERE d.diagnosis_type NOT IN ('Primary', 'Secondary'))
    + (SELECT COUNT(*) FROM phase2.assessment x
       WHERE x.triage_priority_level NOT BETWEEN 1 AND 5)
    + (SELECT COUNT(*) FROM phase2.source_system s
       WHERE s.source_id NOT IN ('A', 'B', 'C', 'D'))

  UNION ALL
  SELECT
    'required_text_values_blank',
    (
      SELECT COUNT(*) FROM phase2.patient p
      WHERE NULLIF(BTRIM(p.full_name), '') IS NULL
    )
    + (SELECT COUNT(*) FROM phase2.admission a
       WHERE NULLIF(BTRIM(a.visit_reason), '') IS NULL
          OR NULLIF(BTRIM(a.admission_source), '') IS NULL)
    + (SELECT COUNT(*) FROM phase2.diagnosis d
       WHERE NULLIF(BTRIM(d.icd9_code), '') IS NULL)
    + (SELECT COUNT(*) FROM phase2.discharge_record d
       WHERE NULLIF(BTRIM(d.discharge_destination), '') IS NULL
          OR NULLIF(BTRIM(d.patient_condition), '') IS NULL)
)
SELECT
  check_name,
  violation_count,
  CASE WHEN violation_count = 0 THEN 'PASS' ELSE 'FAIL' END AS result
FROM checks
ORDER BY check_name;

-- Informational only: detailed discharge_record rows are optional in the
-- current model; do not treat this count as a failure unless the requirement
-- is changed to require one for every closed admission.
SELECT COUNT(*) AS closed_admissions_without_detailed_discharge_record
FROM phase2.admission a
WHERE a.admission_status = 'Closed'
  AND NOT EXISTS (
    SELECT 1
    FROM phase2.discharge_record d
    WHERE d.admission_id = a.admission_id
  );

-- Review current values before adding checks for domains not yet documented.
SELECT 'diagnostic_order.priority' AS domain_name, priority AS value, COUNT(*) AS row_count
FROM phase2.diagnostic_order
GROUP BY priority
UNION ALL
SELECT 'diagnostic_order.order_status', order_status, COUNT(*)
FROM phase2.diagnostic_order
GROUP BY order_status
UNION ALL
SELECT 'diagnostic_examination.examination_status', examination_status, COUNT(*)
FROM phase2.diagnostic_examination
GROUP BY examination_status
UNION ALL
SELECT 'discharge_record.discharge_destination', discharge_destination, COUNT(*)
FROM phase2.discharge_record
GROUP BY discharge_destination
ORDER BY domain_name, value;
