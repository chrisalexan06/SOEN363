TASK 1: INITIAL PROFILE
TXT: UTF-8, pipe (|) delimiter, header first; one file per entity.
CSV: UTF-8, comma delimiter, header first; quoted fields may contain commas/newlines.
Each delimited record follows the field order in its header.
XML: hospital_dataset -> entity -> record -> scalar fields; root attributes are metadata.
JSON: entities -> entity arrays -> record objects; hospital is metadata.
Dates: A YYYY-MM-DD; B DD.MM.YYYY; C YYYY/MM/DD; D DD/MM/YYYY.
Field examples: patient_id / PatientNr / patientNumber / PAT_ID.
Missing: null, blank/whitespace, NULL, N/A, NONE, NAN, NA (case-insensitive).
NA in allergy/medication fields is ambiguous and retained, pending clarification.
Duplicates = exact repeated rows beyond the first occurrence, per source/entity.
Types use all nonmissing values; text or mixed means inference was inconclusive.
Numeric ranges are broad screening assumptions, not clinical diagnostic thresholds.
Original names and values are preserved. Nothing is cleaned or deduplicated.
Malformed records/files: ingestion_errors.jsonl; an empty log means none detected.
Broken quoting stops that file; unreadable XML/JSON is logged as a file failure.
Partial counts cover loaded records only. Check the log before claiming complete totals.
