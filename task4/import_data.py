import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client

# load Supabase credentials from the environment file and create the client.
load_dotenv()
SUPABASE_URL = 'https://saxjkmzgpbhxyecqvrxq.supabase.co'
supabase: Client = create_client(SUPABASE_URL, os.getenv("SUPABASE_KEY"))

# locate the CSV exports and set the maximum number of rows per request.
DATA_DIR = Path(__file__).resolve().parent.parent / "task3_output"
BATCH_SIZE = 500

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
    df = pd.read_csv(csv_path).astype(object)
    df = df.where(pd.notna(df), None)
    records = df.to_dict(orient="records")
# insert each table in batches and have check if it works 
    for batch_number, start in enumerate(range(0, len(records), BATCH_SIZE)):
        batch = records[start : start + BATCH_SIZE]
        supabase.schema("phase2").table(table_name).insert(batch).execute()
        print(f"Inserted {table_name} batch {batch_number}")
