# Revised Phase 2 working project (Tasks 1–2)

All records are entirely fictional and created exclusively for educational and learning purposes. No real patient information is intended. The revised data are a new synthetic scenario, not clinical facts inferred during cleaning.

Run from the project root with Python 3:

```bash
python prepare_admission_types.py
python data_ingestion_and_profiling.py
python data_cleaning_and_standardization.py
python verify_revised_data.py
```

The preparation script reads `uncleaned data/raw/` and writes a separate snapshot under `uncleaned data/raw_with_admission_types/`. It uses `synthetic_revision_plan.json`, a fixed set of synthetic record updates/additions designed for this exact original dataset. Keep the manifest beside the scripts. Do not run it against unrelated raw data. The original raw snapshot and documented injected defects are retained. The plan is generated from the original project's accepted records to select coherent synthetic scenarios; cleaning itself does not manufacture clinical attributes.

The updated mapping includes admission source, date of death, note type/content and an explicit parent diagnostic examination identifier for each radiology examination. The parent and subtype rows represent the same clinical event; count clinical examinations distinctly when needed. New synthetic cases include open admissions, patients without admissions, four critical-care types, transfers, postoperative critical-care stays, recovery notes, death-related discharge records and medication names in place of selected generic placeholders. Existing absence markers must not be treated as medications during Task 3.

A completed admission has a discharge timestamp; a separate detailed discharge record is optional in this revised dataset. 3,552 completed admissions lack a separate detailed discharge record. This is a design decision to confirm with the team/professor: the current Phase 1 FK and uniqueness constraint do not enforce total participation, but if the original business rules require it, further source redesign is needed. Adding one separate row to every such admission would exceed the 40,000-record source limit. Do not fabricate missing discharge details during cleaning. The original report and original generation documentation describe the original snapshot and are historical, not revised results.

Current results: `task1_output/`, `task2_output/cleaning_summary.csv`, `task2_output/cleaning_rules_and_results.json`, `task2_output/revision_verification.json`. The verification script checks coverage scenarios corresponding to the 20 original questions; it does not execute the actual SQL queries, replace database integrity tests, or independently verify clinical correctness of ICD-9 entries. Task 3 must preserve provenance, avoid double-counting radiology subtypes, map local IDs and relationships, and justify schema choices. No Supabase changes were made. Final submission should exclude database and source data as required by the handout; this is a working copy, not a submission ZIP.

Review and disclose AI assistance according to your professor's actual authorization and assignment rules.
