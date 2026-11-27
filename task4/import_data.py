import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client

# load Supabase credentials from the environment file and create the client.
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# locate the CSV exports and set the maximum number of rows per request.
DATA_DIR = Path(__file__).resolve().parent.parent / "task3_output"
BATCH_SIZE = 500

def admission_batches(records, batch_size):
    pending = {}
    for record in records:
        admission_id = int(record["admission_id"])
        if admission_id in pending:
            raise ValueError(f"Duplicate admission_id in import data: {admission_id}")
        pending[admission_id] = record

    admission_ids = set(pending)
    inserted = set()
    while pending:
        ready_ids = []
        for admission_id, record in pending.items():
            parent_id = record["past_record_followup"]
            if parent_id is None:
                ready_ids.append(admission_id)
                continue
            parent_id = int(parent_id)
            if parent_id not in admission_ids:
                raise ValueError(
                    f"past_record_followup {parent_id} is missing from admission.csv"
                )
            if parent_id in inserted:
                ready_ids.append(admission_id)

        if not ready_ids:
            raise ValueError(
                "Admission follow-up references contain a cycle or unresolved parent"
            )

        batch_ids = ready_ids[:batch_size]
        batch = [pending.pop(admission_id) for admission_id in batch_ids]
        yield batch
        inserted.update(batch_ids)

# insert parent tables before dependent tables to satisfy foreign keys.
TABLES_IN_INSERT_ORDER = [
    "source_system",
    "icd9_dictionary",
    "medication",
    "physician",
    "nurse",
    "radiologist",
    "hospital_unit",
    "icd9_source_mapping",
    "patient",
    "admission",
    "diagnosis",
    "primary_diagnosis",
    "secondary_diagnosis",
    "diagnostic_order",
    "unit_stay",
    "surgical_procedure",
    "clinical_note",
    "assessment",
    "assessment_reported_symptoms",
    "assessment_known_allergies",
    "current_meds",
    "diagnostic_examination",
    "blood_test",
    "ct_examination",
    "electrodiagram",
    "radiology_examination",
    "discharge_record",
    "radiology_report",
    "discharge_record_secondary_diagnosis",
    "discharge_summary",
    "discharge_record_primary_diagnosis",
    "prescribed_meds",
]

# check all required CSVs up front to avoid a partial import from missing files.
missing_files = [
    table_name
    for table_name in TABLES_IN_INSERT_ORDER
    if not (DATA_DIR / f"{table_name}.csv").is_file() # if not in directory, not there
]
if missing_files:
    raise FileNotFoundError(
        f"Missing CSV files in {DATA_DIR}: {', '.join(missing_files)}" # error if missing
    )

# convert each CSV into records, replacing empty values with nulls, according to the Supabase documentation for importing 
for table_name in TABLES_IN_INSERT_ORDER:
    csv_path = DATA_DIR / f"{table_name}.csv"
    df = pd.read_csv(csv_path)

    if table_name == "patient":
        for column in ("physician_id", "nurse_id"):
            df[column] = pd.to_numeric(df[column], errors="raise").astype("Int64")

    if table_name == "admission":
        df["past_record_followup"] = pd.to_numeric(
            df["past_record_followup"], errors="raise"
        ).astype("Int64")
    df = df.astype(object)
    df = df.where(pd.notna(df), None)
    records = df.to_dict(orient="records")

# insert each table in batches and have check if it works
    if table_name == "admission":
        batches = admission_batches(records, BATCH_SIZE)
    else:
        batches = (
            records[start : start + BATCH_SIZE]
            for start in range(0, len(records), BATCH_SIZE)
        )

    for batch_number, batch in enumerate(batches):
        supabase.schema("phase2").table(table_name).upsert(batch).execute()
        print(f"Inserted {table_name} batch {batch_number}")
