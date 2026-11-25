# SOEN 363 — Phase 2 Synthetic Hospital Data Sources

Generated reproducibly with `generate.py`. **All patients, clinicians, contact information, examinations, and records are fictional.** Historical ICD-9 codes only; not for real-world medical coding.

## Geographic origins and formats

| Source | Continent | Country | Source format | Raw entity records |
|---|---|---|---|---:|
| A | North America | Canada | TXT | 9,438 |
| B | Europe | Germany | CSV | 9,438 |
| C | Asia | Japan | XML | 9,438 |
| D | Africa | South Africa | JSON | 9,438 |
| **Total** | | | | **37,752** |

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
| ambiguous_date | 24 | 0.06% |
| broken_reference | 48 | 0.13% |
| case_whitespace | 160 | 0.42% |
| chronology | 48 | 0.13% |
| exact_duplicate | 96 | 0.25% |
| invalid_date | 24 | 0.06% |
| invalid_numeric | 56 | 0.15% |
| missing_optional | 104 | 0.28% |
| missing_required | 48 | 0.13% |

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
| Raw records across four systems | 37,752 |
| Total removed / deduplicated | 360 |
| **Retained integrated entity records** | **37,392** |

Removal reasons (one reason per removed row):

| Reason | Rows |
|---|---:|
| broken_reference | 48 |
| chronology | 48 |
| deduplicated | 96 |
| invalid_or_ambiguous_date | 48 |
| missing_required_icd9 | 24 |
| missing_required_physician | 24 |
| shared_reference_dictionary | 72 |

For complete per-entity source-to-cleaned reconciliation see `documentation/record_counts_by_source_entity.csv`; for per-row reasons see `documentation/rejected_or_deduplicated_rows.csv`.

## Evidence for the four Phase 1 query scenarios

- Admissions with >1 distinct ICD-9 code: **2,552**
- Patients with >1 clinical note (latest-note query): **176**
- Admission/date combinations having both surgery and radiology: **238**
- Primary diagnoses recorded for deceased patients: **328**

## ICD-9 verification and historical limitations

The dictionary uses **24 historical ICD-9-CM diagnosis codes with descriptions** from the final U.S. 2015 ICD-9-CM code set. Primary reference is CMS: https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-9-cm-diagnosis-procedure-codes-abbreviated-and-full-code-titles . CMS distributes Version 32 full and abbreviated titles (effective October 1, 2014). The code/title pairs have been cross-checked against publicly accessible legacy ICD-9-CM code references; a per-code verification URL is recorded in `documentation/icd9_code_verification.csv`. For an additional final check, compare with the downloadable official CMS V32 source file before submission. This generator does not redistribute an official dictionary file. Since 2015 these are legacy codes, included solely because the assignment explicitly requires ICD-9.

## Files

- `raw/`: original source files in **only each assigned format**; source metadata lives in `documentation/SOURCE_INFO_*.md`
- `cleaned_integrated/`: normalized CSV preview across four hospitals
- `documentation/record_counts_by_source_entity.csv`: detailed record counts and removals
- `documentation/injected_quality_issues.csv`: exactly where/how issues were inserted
- `documentation/rejected_or_deduplicated_rows.csv`: actual removal audit
- `documentation/schema_field_mapping.csv`: canonical and native column mapping, PK/FK design
- `documentation/validation_report.json`: machine-readable validation results
- `documentation/icd9_code_verification.csv`: legacy code-by-code reference links
- `documentation/raw_sha256_checksums.csv`: original-source SHA-256 fingerprints
- `reference/ERdiagram.drawio`: untouched reference diagram copy
- `generate.py`: deterministic generator; rerun with Python and Faker installed to reconstruct dataset

**Important scope note:** `hospital_units` is a documented extension; the ERD's other inheritance structures are represented by discriminator fields rather than repeating the same instance twice. Generated values are mock data, not clinical guidance.
