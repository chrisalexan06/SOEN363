"""Task 2. Run this file after Task 1; requires only the standard library.

Reads original files using Task 1's loaders. Never runs the data generator.
Keeps sources and local identifiers separate; global SQL IDs belong to Task 3.
"""

# Count outcomes with Counter and collect groups with defaultdict.
from collections import Counter, defaultdict

# Read field mappings and write tabular cleaning reports.
import csv

# Parse dates/times and calculate procedure end times.
from datetime import datetime, timedelta


# Serialize cleaned records, review datasets and documented rules.
import json

# Construct portable paths relative to this script.
from pathlib import Path

# Recognize formats and normalize whitespace using regular expressions.
import re

# Reuse Task 1 loaders without automatically calling its main function.
import data_ingestion_and_profiling as task1

# Find the project directory containing this script.
BASE = Path(__file__).resolve().parent

# Keep Task 2 results separate from the original data and Task 1 outputs.
OUTPUT = BASE / "task2_output"

# Locate the CSV describing canonical fields, source aliases and relationships.
MAPPING = BASE / "task2_field_mapping.csv"

# Associate each source letter with its alias column in the mapping CSV.
SOURCE_COLUMNS = dict(zip("ABCD", ["source_A_TXT", "source_B_CSV", "source_C_XML", "source_D_JSON"]))


# Recognize documented missing markers; literal None text is deliberately excluded.
MISSING = {"", "na", "n/a", "null", "nan", "k.a.", "未記録", "-"}

# Define broad numeric screening bounds; (None, None) means no range is assumed.
NUMBERS = {
    'body_temperature': (25, 45),

    'heart_rate': (1, 300),

    'respiratory_rate': (1, 100),

    'oxygen_saturation': (0, 100),

    'pain_level': (0, 10),

    'triage_priority_level': (1, 5),

    'duration_minutes': (1, 10080),

    'capacity_beds': (1, 10000),

    'bed_number': (1, 10000),

    'result_value': (None, None),
}

# Require whole numbers except for the three fields that permit decimals.
INTEGER_FIELDS = set(NUMBERS) - {"body_temperature", "oxygen_saturation", "result_value"}

# Identify synthetic personal-name fields eligible for display capitalization.
NAME_FIELDS = {"full_name", "nurse_name", "physician_name", "radiologist_name", "responsible_physician"}

# Identify each entity's event prefix, such as note_date/note_time for clinical notes.
EVENTS = {
    'assessments': 'assessment',

    'diagnoses': 'diagnosis',

    'clinical_notes': 'note',

    'diagnostic_orders': 'request',

    'diagnostic_examinations': 'examination',

    'radiology_examinations': 'examination',

    'radiology_reports': 'report',

    'surgical_procedures': 'procedure',

    'discharge_records': 'discharge',
}
# Requiredness is an explicit project policy; optional fields are retained as null.

# Declare mandatory clinical fields; read_schema also adds primary and foreign keys.
REQUIRED = {
    'hospital_units': 'unit_name unit_type ward capacity_beds',

    'nurses': 'nurse_name',

    'physicians': 'physician_name',

    'radiologists': 'radiologist_name',

    'icd9_dictionary': 'diagnosis_title description',

    'patients': 'full_name date_of_birth gender life_status',

    'admissions': 'admission_date admission_time admission_type admission_source admission_status visit_reason is_followup',

    'assessments': 'assessment_date assessment_time triage_priority_level',

    'unit_stays': 'unit_type ward entry_date entry_time',

    'diagnoses': 'diagnosis_date diagnosis_time diagnosis_type',

    'clinical_notes': 'note_date note_time medical_condition note_type note_contents',

    'diagnostic_orders': 'request_date request_time priority requested_examination order_status',

    'diagnostic_examinations': 'examination_date examination_time examination_type examination_status',

    'radiology_examinations': 'examination_date examination_time examination_type examination_status',

    'radiology_reports': 'report_date report_time findings',

    'surgical_procedures': 'procedure_date procedure_time procedure_type duration_minutes',

    'discharge_records': 'discharge_date discharge_time discharge_destination patient_condition',

    'discharge_summaries': 'admission_reason recommendations',
}


# Build a case-insensitive lookup from localized category labels to standard values.
def category_map(groups):

    # Include standard spellings and aliases; casefold makes comparisons case-insensitive.
    return {alias.casefold(): standard for standard, aliases in groups.items()
            for alias in [standard] + aliases}


# Translate source labels into common categories; unsupported labels require review.
CATEGORIES = {
    # Standardize generated admission types independently of admission status.
    'admission_type': category_map({
        'Emergency': ['Notfall', '緊急'],

        'Elective': ['Geplant', '予定'],
    }),

    # Map English, German-letter and Japanese gender labels.
    'admission_source': category_map({
        'Emergency Department': ['Notaufnahme', '救急外来', 'ED'],
        'Physician Referral': ['Arztüberweisung', '医師紹介', 'PHYSICIAN_REFERRAL'],
        'Hospital Transfer': ['Krankenhausverlegung', '転院', 'HOSPITAL_TRANSFER'],
    }),
    'gender': category_map({
        'Male': ['M', '男'],

        'Female': ['F', '女'],

        'Other': ['X', 'その他'],
    }),

    # Use Alive or Deceased for all sources.
    'life_status': category_map({
        'Alive': ['Lebend', '生存'],

        'Deceased': ['Verstorben', '死亡', 'DEAD'],
    }),

    # Use Primary or Secondary regardless of source spelling.
    'diagnosis_type': category_map({
        'Primary': ['Haupt', '主'],

        'Secondary': ['Neben', '副'],
    }),

    # Translate hospital-unit types to the same five common labels.
    'unit_type': category_map({
        'ED': ['Notaufnahme', '救急', 'EMERGENCY'],

        'General Ward': ['Normalstation', '一般病棟', 'WARD'],

        'ICU': ['Intensivstation', '集中治療'],
        'MICU': [], 'SICU': [], 'CCU': [],

        'Surgical Ward': ['Chirurgie', '外科病棟', 'SURGICAL'],

        'Recovery': ['Aufwachraum', '回復室'],
    }),

    # Map routine, urgent and immediate order priorities.
    'priority': category_map({
        'Routine': ['Normal', '通常', 'LOW'],

        'Urgent': ['Hoch', '緊急', 'HIGH'],

        'Stat': ['Sofort', '至急', 'CRITICAL'],
    }),

    # Use Closed or Open for admission status.
    'admission_status': category_map({
        'Closed': ['Completed', 'Discharged'],

        'Open': ['Active', 'Admitted'],
    }),

    # Standardize order completion and cancellation labels.
    'order_status': category_map({
        'Completed': [],

        'Pending': [],

        'Cancelled': ['Canceled'],
    }),

    # Apply a common vocabulary to examination status.
    'examination_status': category_map({
        'Completed': [],

        'Pending': [],

        'Cancelled': ['Canceled'],
    }),

    # Recognize Celsius and Fahrenheit spellings before conversion.
    'temperature_unit': category_map({
        'C': ['°C', 'Celsius'],

        'F': ['°F', 'Fahrenheit'],
    }),
}


# Read canonical fields, source aliases, primary keys, references and required-field policies.
def read_schema():

    # Group mapping rows by entity and canonical field name.
    schema = defaultdict(dict)

    # Open the mapping CSV, allowing a UTF-8 byte-order mark.
    with MAPPING.open(encoding="utf-8-sig", newline="") as file:

        # Read each mapping row as a dictionary using the CSV header.
        for item in csv.DictReader(file):

            # Keep each field's aliases, key flags and reference metadata.
            schema[item["entity"]][item["canonical_field"]] = item

    # Find the field marked as the primary key in each entity.
    keys = {entity: next(field for field, item in fields.items() if item["primary_key"] == "True")
            for entity, fields in schema.items()}

    # Collect each foreign-key field and the parent entity it references.
    foreign = {entity: {field: item["foreign_key_target"] for field, item in fields.items()
                        if item["foreign_key_target"]} for entity, fields in schema.items()}

    # Validate optional secondary diagnosis codes against the dictionary as well.
    foreign["discharge_records"]["secondary_icd9_code"] = "icd9_dictionary"

    # Combine explicit required fields with primary-key and foreign-key requirements.
    required = {entity: set(REQUIRED[entity].split()) | {keys[entity]} | set(foreign[entity])
                for entity in schema}

    # Allow missing assigned nurse/physician links in patient records.
    required["patients"] -= {"nurse_id", "physician_id"}  # Optional assigned professionals.

    # Do not require a secondary diagnosis for every discharge.
    required["discharge_records"].discard("secondary_icd9_code")

    # Return the schema and policies used by the cleaning functions.
    return dict(schema), keys, foreign, required


# Write record dictionaries to a CSV file using a defined column order.
def save_csv(path, rows, fields):

    # Create the report directory and any missing parent directories.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Overwrite this report using UTF-8 and CSV-managed line endings.
    with path.open("w", encoding="utf-8-sig", newline="") as file:

        # Place each dictionary value in its named output column.
        writer = csv.DictWriter(file, fieldnames=fields)

        # Write the CSV column headings before the records.
        writer.writeheader()

        # Write all report rows; None becomes an empty CSV cell.
        writer.writerows(rows)


# Create a stable JSON representation for record comparison and logging.
def fingerprint(value):

    # Sort keys for stable comparisons, preserve Unicode and reject non-finite JSON numbers.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)




# Load original data using Task 1 parsers, and stop if ingestion is incomplete.
def load_sources(schema):

    # Keep each hospital source's entity tables separate.
    sources = {}

    # Use a Task 2 ingestion log independent of the Task 1 reports.
    log_path = OUTPUT / "ingestion_errors.jsonl"

    # Start a fresh error log for this run and close it automatically afterward.
    with log_path.open("w", encoding="utf-8") as log:

        # Use the source folder definitions already established in Task 1.
        for source, (folder, _) in task1.SOURCES.items():

            # Resolve the raw input folder for the current source.
            directory = task1.RAW / folder

            # A and B use one delimited file per entity; C and D use nested documents.
            if source in "AB":

                # Select pipe-delimited TXT for A or comma-delimited CSV for B.
                extension, delimiter = ("txt", "|") if source == "A" else ("csv", ",")

                # Load every mapped entity; Task 1 logs missing or malformed input.
                tables = {entity: task1.load_table(directory / f"{entity}.{extension}", delimiter, source, log)
                          for entity in schema}

                # Find entity files absent from the mapping instead of silently ignoring them.
                unexpected = {p.stem for p in directory.glob(f"*.{extension}")} - schema.keys()

                # An unmapped entity needs review before cleaning can be considered complete.
                if unexpected:

                    # Record the unexpected or missing entity information in the ingestion log.
                    task1.log_error(log, source, directory, "entities", f"Unmapped entities: {unexpected}")
            else:

                # Extract XML records for source C or JSON entity arrays for source D.
                tables = task1.load_nested(directory / ("hospital.xml" if source == "C" else "hospital.json"), source, log)

                # Check that the nested document contains exactly the expected entity groups.
                if tables.keys() != schema.keys():

                    # Record the unexpected or missing entity information in the ingestion log.
                    task1.log_error(log, source, directory, "entities", "Entity set differs from mapping")

            # Save the loaded tables under their source letter.
            sources[source] = tables

    # A nonempty log indicates that inputs were not completely and safely loaded.
    if log_path.stat().st_size:

        # Stop before writing new cleaned datasets; leave the log available for review.
        raise ValueError("Input could not be completely loaded. See task2_output/ingestion_errors.jsonl; no new cleaned outputs written.")

    # Pass the completely loaded source tables to normalization.
    return sources


# Standardize one field using explicit source formats and field-specific rules.
def convert_value(field, value, source):

    # Recognize actual nulls and documented missing markers before attempting conversions.
    if value is None or (isinstance(value, str) and value.strip().casefold() in MISSING):

        # Represent absent information as None without inventing a replacement.
        return None

    # Collapse repeated whitespace and remove leading/trailing spaces.
    text = re.sub(r"\s+", " ", str(value)).strip()

    # Treat hospital-local identifiers separately from clinical codes.
    if field.endswith("_id"):

        # Require a positive digit-only local ID and reject booleans.
        if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", text) or int(text) < 1:

            # Report the invalid ID so normalization can quarantine its record.
            raise ValueError("Expected positive local integer identifier")

        # Store a valid local integer ID as consistent text, still scoped to its source.
        return str(int(text))

    # Preserve ICD-9 codes as strings so leading zeros and dots survive.
    if "icd9" in field:

        # Numeric ICD-9 input may already have lost significant formatting.
        if not isinstance(value, str):

            # Reject numeric codes instead of reconstructing a potentially incorrect code.
            raise ValueError("ICD-9 must be supplied as text; lost leading zeros cannot be reconstructed")

        # Return the code text after whitespace normalization, without numeric conversion.
        return text  # Never convert ICD-9 to float.

    # Recognize event dates, birth dates and optional follow-up dates.
    if field.endswith("_date") or field in {"date_of_birth", "date_of_death", "follow_up_appointment"}:

        # Retrieve the documented date pattern for the current source.
        pattern = task1.SOURCES[source][1]

        # Require exact separators and a four-digit year rather than guessing layouts.
        layouts = {"A": r"\d{4}-\d{2}-\d{2}", "B": r"\d{2}\.\d{2}\.\d{4}",
                   "C": r"\d{4}/\d{2}/\d{2}", "D": r"\d{2}/\d{2}/\d{4}"}

        # Check the complete string against its source's date layout.
        if not re.fullmatch(layouts[source], text):

            # Reject unexpected or ambiguous layouts for manual review.
            raise ValueError("Invalid or ambiguous date layout; no date guessing")

        # Validate the calendar date and produce ISO YYYY-MM-DD text.
        return datetime.strptime(text, pattern).date().isoformat()

    # Standardize times to one consistent 24-hour representation.
    if field.endswith("_time"):

        # The German source uses dots between time components.
        if source == "B":

            # Convert a German time such as 09.30 into 09:30.
            text = text.replace(".", ":")

        # Accept hours/minutes with optional seconds, requiring two-digit components.
        if not re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", text):

            # Reject malformed time strings rather than assume a time.
            raise ValueError("Invalid time layout")

        # Validate the clock time and return HH:MM:SS text.
        return datetime.strptime(text, "%H:%M:%S" if text.count(":") == 2 else "%H:%M").strftime("%H:%M:%S")

    # Interpret the supported English, German and numeric boolean tokens.
    if field == "is_followup":

        # Check the token against all supported true/false spellings.
        if text.casefold() not in {"yes", "no", "ja", "nein", "true", "false", "1", "0"}:

            # Do not automatically turn an unrecognized boolean token into False.
            raise ValueError("Unknown boolean token")

        # Return a real Python boolean for a recognized token.
        return text.casefold() in {"yes", "ja", "true", "1"}

    # Translate categorical fields only through documented mappings.
    if field in CATEGORIES:

        # Detect categorical values that are absent from the mapping.
        if text.casefold() not in CATEGORIES[field]:

            # Require review instead of inventing an unfamiliar category's meaning.
            raise ValueError("Unknown category; mapping requires review")

        # Return the common category label associated with the source spelling.
        return CATEGORIES[field][text.casefold()]

    # Convert only fields explicitly declared numeric.
    if field in NUMBERS:

        # Reject nonnumeric, boolean or non-finite measurements.
        if not task1.numeric(value):

            # Let normalization decide whether to null an optional value or quarantine.
            raise ValueError("Invalid/non-finite number")

        # Parse the measurement before checking its integer requirement and range.
        result = float(value)

        # Whole-number fields must not contain a fractional component.
        if field in INTEGER_FIELDS and not result.is_integer():

            # Do not round an unexpected fractional value into a made-up integer.
            raise ValueError("Expected a whole number")
        # Temperature is range-checked after unit conversion.

        # Retrieve the broad screening range for this numeric field.
        low, high = NUMBERS[field]

        # Check ordinary ranges now; temperature requires unit conversion first.
        if field != "body_temperature" and low is not None and not low <= result <= high:

            # Report a measurement outside its documented screening bounds.
            raise ValueError(f"Outside documented range [{low}, {high}]")

        # Return an integer for whole-number fields or a float for decimal fields.
        return int(result) if field in INTEGER_FIELDS else result

    # Apply the synthetic-name display convention outside the Japanese source.
    if field in NAME_FIELDS and source != "C":

        # Normalize display capitalization; preserve original spelling in the raw source and representative examples.
        return text.title()  # Synthetic-name display convention; original remains in the raw source.

    # Keep other text capitalization unchanged after whitespace normalization.
    return text


# Clean one record and return its standardized fields, unresolved errors and change audit.
def normalize(source, entity, raw, schema, required):

    # Keep cleaned values, unresolved record problems and transformation details separately.
    row, errors, changes = {}, [], []

    # Identify the source field names that the mapping expects for this entity.
    aliases = {item[SOURCE_COLUMNS[source]] for item in schema[entity].values()}

    # Detect unmapped fields instead of silently losing their contents.
    if raw.keys() - aliases:

        # Add the unknown fields as a record-level quarantine reason.
        errors.append("Unmapped fields: " + ", ".join(sorted(raw.keys() - aliases)))

    # Visit each canonical field and its source-specific alias.
    for field, item in schema[entity].items():

        # Retrieve the original source value, using None for an absent field.
        original = raw.get(item[SOURCE_COLUMNS[source]])

        # Attempt this field's conversion without stopping the entire dataset.
        try:

            # Store the standardized value under its canonical name.
            row[field] = convert_value(field, original, source)
        except (ValueError, TypeError, OverflowError) as error:

            # Use null for the failed value while recording its disposition below.
            row[field] = None

            # Invalid optional numeric measurements may remain in accepted records as null.
            if field in NUMBERS and field not in required[entity]:

                # Record why this optional measurement was cleared.
                changes.append((field, original, None, f"invalid_optional_to_null: {error}"))
            else:

                # Other unresolved conversion failures make the record unsuitable for acceptance.
                errors.append(f"{field}: {error}")

    # Apply the assessment-specific temperature and blood-pressure checks.
    if entity == "assessments":

        # Read the parsed temperature together with its declared unit.
        temperature, unit = row.get("body_temperature"), row.get("temperature_unit")

        # Skip measurement conversion when the temperature is absent.
        if temperature is not None:

            # Remember the reading for the audit if it proves invalid.
            original = temperature

            # Convert only readings explicitly labeled Fahrenheit.
            if unit == "F":

                # Calculate Celsius using (F - 32) * 5/9, rounded to one decimal place.
                temperature = round((temperature - 32) * 5 / 9, 1)

            # Flag unknown units or a converted temperature outside the Celsius screening range.
            if unit not in {"C", "F"} or not 25 <= temperature <= 45:

                # Retain the assessment with a null optional temperature.
                row["body_temperature"] = None

                # Audit the invalid temperature with its specific nulling reason.
                changes.append(("body_temperature", original, None, "invalid_temperature_to_null"))
            else:

                # Retain the valid temperature expressed in Celsius.
                row["body_temperature"] = temperature

            # Use the common Celsius label only when the original unit was recognized.
            if unit in {"C", "F"}:

                # Store the standardized temperature unit.
                row["temperature_unit"] = "C"

        # Retrieve the optional blood-pressure string.
        pressure = row.get("blood_pressure")

        # Only validate blood pressure when the source supplies a reading.
        if pressure is not None:

            # Recognize systolic/diastolic notation such as 120/80.
            match = re.fullmatch(r"(\d{2,3})\s*/\s*(\d{2,3})", pressure)

            # Check the pair's structure, positive lower pressure and broad upper bound.
            if not match or not 0 < int(match[2]) < int(match[1]) <= 300:

                # Clear an invalid optional blood-pressure measurement while retaining the assessment.
                row["blood_pressure"] = None

                # Audit the blood-pressure value that was replaced with null.
                changes.append(("blood_pressure", pressure, None, "invalid_optional_to_null"))

    # Apply this entity's required-field policy to the final converted values.
    for field in required[entity]:

        # A missing or failed required value cannot be accepted.
        if row.get(field) is None:

            # Record which required field is unavailable.
            errors.append(f"Missing required field: {field}")
    # Store explicit local timestamps without inventing a UTC offset.

    # Use a snapshot of names because new timestamp fields will be added.
    for field in list(row):

        # Combine dates only when a corresponding time field is defined.
        if field.endswith("_date") and field[:-5] + "_time" in row:

            # Remove _date to obtain the event prefix, such as admission.
            prefix = field[:-5]

            # Read the event's standardized date and time components.
            date, time = row[field], row[prefix + "_time"]

            # Detect a date without a time or a time without a date.
            if (date is None) != (time is None):

                # Flag incomplete pairs instead of assuming midnight or inventing a date.
                errors.append(f"Incomplete date/time pair: {prefix}")

            # Construct an ISO local timestamp; preserve null when both parts are absent.
            row[prefix + "_timestamp"] = f"{date}T{time}" if date and time else None

    # Visit each canonical field and its source-specific alias.
    for field, item in schema[entity].items():

        # Retrieve the original source value, using None for an absent field.
        original = raw.get(item[SOURCE_COLUMNS[source]])

        # Audit type changes as well as changes in a field's value.
        if type(original) != type(row[field]) or original != row[field]:

            # Preserve before/after values with the standardization action.
            changes.append((field, original, row[field], "standardize_or_null"))

    # Return cleaned values, unique sorted errors and every recorded field operation.
    return row, sorted(set(errors)), changes


# Remove confirmed extra copies within a source; quarantine conflicting or uncertain entities.
def find_duplicates(entries, keys):
    """Within-source only: exact copies, identical local entities, and conflicts."""

    # Track exact raw copies and records sharing a standardized primary key.
    exact, groups = {}, defaultdict(list)

    # Inspect records without comparing unrelated hospitals as one source.
    for entry in entries:

        # Restrict duplicate matching to one source and one entity type.
        scope = (entry["source"], entry["entity"])

        # Combine that scope with the complete original record contents.
        signature = scope + (fingerprint(entry["original"]),)

        # A previously seen signature identifies an exact extra copy.
        if signature in exact:

            # Remove the extra copy from accepted data while retaining it in the duplicate log.
            entry["status"] = "duplicate_removed"

            # Identify the earlier source record represented by this extra copy.
            entry["reasons"] = [f"Exact duplicate of source record {exact[signature]}"]

            # No further duplicate decision is needed for this exact copy or singleton group.
            continue

        # Remember the first source record with these complete raw contents.
        exact[signature] = entry["record_number"]

        # Look up the entity's standardized local primary key.
        key = entry["cleaned"].get(keys[entry["entity"]])

        # Only known primary keys can be grouped for key-based matching.
        if key is not None:

            # Collect records with the same source, entity type and local key.
            groups[scope + (key,)].append(entry)

    # Review shared-key groups for conflicting or identical entities.
    for group in groups.values():

        # A single occurrence has no competing record under its key.
        if len(group) < 2:

            # No further duplicate decision is needed for this exact copy or singleton group.
            continue

        # Different standardized contents under one key indicate an unresolved conflict.
        if len({fingerprint(e["cleaned"]) for e in group}) > 1:

            # Apply the review decision to every conflicting or uncertain record.
            for entry in group:

                # Retain uncertain records for manual review instead of accepting an arbitrary version.
                entry["status"] = "quarantined"

                # Explain that the same local key has conflicting contents.
                entry["reasons"].append("Conflicting records share the same source-local primary key")

        # Only error-free records with identical standardized contents can be deduplicated.
        elif not any(e["reasons"] for e in group):

            # Keep the first standardized entity and classify subsequent copies as duplicates.
            for entry in group[1:]:

                # Remove the extra copy from accepted data while retaining it in the duplicate log.
                entry["status"] = "duplicate_removed"

                # Distinguish an identical standardized entity from an exact raw duplicate.
                entry["reasons"] = ["Same source-local key and identical standardized entity"]

    # Prepare a separate review grouping for patients with different local IDs.
    candidates = defaultdict(list)

    # Inspect records without comparing unrelated hospitals as one source.
    for entry in entries:

        # Use standardized patient attributes for the candidate-matching rule.
        row = entry["cleaned"]

        # Consider only patient records still eligible for acceptance.
        if entry["entity"] == "patients" and entry["status"] is None:

            # Use insurance number and birth date together; a name alone is not sufficient.
            insurance, birth = row.get("health_insurance_number"), row.get("date_of_birth")

            # Do not attempt this patient match when identifying information is missing.
            if insurance and birth:

                # Group the insurance/birth-date pair within the same hospital source only.
                candidates[(entry["source"], insurance.casefold(), birth)].append(entry)

    # Inspect groups that could describe one patient under several IDs.
    for group in candidates.values():

        # Several surviving IDs for the same pair require manual review, not automatic merging.
        if len(group) > 1:

            # Apply the review decision to every conflicting or uncertain record.
            for entry in group:

                # Retain uncertain records for manual review instead of accepting an arbitrary version.
                entry["status"] = "quarantined"

                # Document the exact patient-matching evidence behind quarantine.
                entry["reasons"] = ["Possible duplicate patient: same insurance number and birth date, different local IDs; manual review"]


# Read an ISO local timestamp as a Python datetime for chronological comparisons.
def stamp(row, prefix):

    # Find the timestamp field associated with the event prefix.
    value = row.get(prefix + "_timestamp")

    # Parse an existing ISO timestamp or return None when it is absent.
    return datetime.fromisoformat(value) if value else None


# Check parent references, linked-record consistency and hospital-event chronology.
def relationship_errors(entity, row, index, keys, foreign):

    # Collect all detected issues so the quarantine explanation can show multiple problems.
    errors = []

    # Visit every declared foreign key for the current entity.
    for field, parent in foreign[entity].items():

        # Read the referenced local identifier or ICD-9 code.
        value = row.get(field)

        # Allow optional null references but require supplied references to resolve.
        if value is not None and value not in index[parent]:

            # Flag a parent that is absent or has been removed from accepted data.
            errors.append(f"Missing accepted parent: {field}={value} -> {parent}")

    # Find the accepted admission linked directly from this record, if present.
    admission = index["admissions"].get(row.get("admission_id"))

    # The explicit patient ID must agree with the patient on the linked admission.
    if admission and row.get("patient_id") and row["patient_id"] != admission["patient_id"]:

        # Record inconsistent patient/admission identifiers.
        errors.append("Patient/admission identifiers disagree")

    # Validate examinations against the diagnostic orders they reference.
    if entity in {"diagnostic_examinations", "radiology_examinations"}:

        # Find the accepted diagnostic order for this examination.
        order = index["diagnostic_orders"].get(row.get("diagnostic_order_id"))

        # Require the examination and its order to belong to the same admission.
        if order and order["admission_id"] != row["admission_id"]:

            # Flag inconsistent order/admission links.
            errors.append("Examination and order belong to different admissions")

        # An examination must not occur before the request ordering it.
        if order and stamp(row, "examination") < stamp(order, "request"):

            # Record an examination/request chronology violation.
            errors.append("Examination precedes its order")

    if entity == "radiology_examinations":
        parent = index["diagnostic_examinations"].get(row.get("examination_id"))
        if parent and any(parent.get(field) != row.get(field) for field in
                          ("admission_id", "diagnostic_order_id", "examination_type", "examination_timestamp")):
            errors.append("Radiology examination disagrees with parent examination")

    if entity == "patients":
        death = row.get("date_of_death")
        if row.get("life_status") == "Deceased" and not death:
            errors.append("Deceased patient lacks date of death")
        if row.get("life_status") == "Alive" and death:
            errors.append("Living patient has date of death")
        if death and death < row["date_of_birth"]:
            errors.append("Death precedes birth")

    # Check the summary's discharge-record link and listed diagnosis codes.
    if entity == "discharge_summaries":

        # Look up the accepted discharge record referenced by the summary.
        discharge = index["discharge_records"].get(row.get("discharge_record_id"))

        # The summary and its discharge record must refer to the same admission.
        if discharge and discharge["admission_id"] != row["admission_id"]:

            # Record an inconsistent summary/admission link.
            errors.append("Discharge summary and discharge record disagree on admission")

        # Support diagnosis-code lists separated by commas or semicolons.
        codes = re.split(r"[;,]\s*", row.get("icd9_code_diagnoses") or "")

        # Require each nonempty listed diagnosis code to exist in the accepted dictionary.
        if any(code and code not in index["icd9_dictionary"] for code in codes):

            # Record unknown ICD-9 references in a discharge summary.
            errors.append("Discharge summary refers to an unknown ICD-9 code")

    # Check the referenced unit's metadata or the unit stay's chronological endpoints.
    if entity == "unit_stays":

        # Find the hospital unit referenced by this stay.
        unit = index["hospital_units"].get(row.get("hospital_unit_id"))

        # Compare the stay's unit type and ward against the referenced unit.
        if unit and any(row[field] != unit[field] for field in ("unit_type", "ward")):

            # Flag conflicting unit information rather than choosing which version is true.
            errors.append("Unit stay disagrees with referenced unit type or ward")

    # Follow the radiology report's examination link to validate its timing.
    if entity == "radiology_reports":

        # Retrieve the accepted examination described by this report.
        examination = index["radiology_examinations"].get(row.get("radiology_examination_id"))

        # Use examination details only when the referenced parent exists.
        if examination:

            # Derive the report's admission from its examination's known link.
            admission = index["admissions"].get(examination["admission_id"])

            # A report must not precede the examination it describes.
            if stamp(row, "report") < stamp(examination, "examination"):

                # Record invalid report/examination chronology.
                errors.append("Radiology report precedes its examination")

    # Check admission status, discharge order and the patient's birth date.
    if entity == "admissions":

        # Read the admission's opening timestamp and optional discharge timestamp.
        start, end = stamp(row, "admission"), stamp(row, "discharge")

        # A completed admission must have a known discharge timestamp.
        if row["admission_status"] == "Closed" and not end:

            # Record missing discharge information for a completed admission.
            errors.append("Completed admission has no discharge timestamp")

        # An open admission must not contradict a supplied discharge timestamp.
        if row["admission_status"] == "Open" and end:

            # Record contradictory admission-status and discharge information.
            errors.append("Open admission has a discharge timestamp")

        # Require discharge after admission, or unit exit after entry.
        if end and end <= start:

            # Record discharge at or before the beginning of the admission.
            errors.append("Discharge must occur after admission")

        # Find the accepted patient associated with this admission.
        patient = index["patients"].get(row.get("patient_id"))

        # An admission cannot occur before the patient's documented birth date.
        if patient and patient["date_of_birth"] > row["admission_date"]:

            # Record the impossible birth/admission sequence.
            errors.append("Admission occurs before patient's birth")

        if patient and patient.get("date_of_death"):
            death = patient["date_of_death"]
            if row["admission_date"] > death or (row.get("discharge_date") and row["discharge_date"] > death):
                errors.append("Admission extends beyond patient death")

    # Check the referenced unit's metadata or the unit stay's chronological endpoints.
    if entity == "unit_stays":

        # Read the unit stay's entry and optional exit timestamps.
        start, end = stamp(row, "entry"), stamp(row, "exit")

        # Require discharge after admission, or unit exit after entry.
        if end and end <= start:

            # Record an exit timestamp that is not later than entry.
            errors.append("Unit exit must occur after entry")

        # A stay within a completed admission needs a recorded exit.
        if admission and stamp(admission, "discharge") and not end:

            # Flag an unfinished unit stay within a discharged admission.
            errors.append("Unit stay in completed admission has no exit timestamp")

    # Validate linked event times against the known admission period in this source.
    if admission:

        # Use the parent admission's start and optional discharge as boundaries.
        start, end = stamp(admission, "admission"), stamp(admission, "discharge")

        # Check both endpoints of a unit stay or the single event timestamp for other entities.
        prefixes = ["entry", "exit"] if entity == "unit_stays" else [EVENTS.get(entity)]

        # Inspect each event timestamp relevant to this entity.
        for prefix in prefixes:

            # Retrieve the event time, or None for an entity without a timed event.
            event = stamp(row, prefix) if prefix else None

            # Require events at/after admission and at/before a known discharge.
            if event and (event < start or (end and event > end)):

                # Identify the event outside its admission period.
                errors.append(f"{prefix} timestamp is outside its admission period")

        # Validate the procedure's calculated finish time as well as its start.
        if entity == "surgical_procedures":

            # Add the documented duration to the procedure start timestamp.
            finish = stamp(row, "procedure") + timedelta(minutes=row["duration_minutes"])

            # The procedure must finish before or at the known discharge time.
            if end and finish > end:

                # Record a procedure duration that extends beyond discharge.
                errors.append("Procedure duration extends beyond discharge")

        # Compare a discharge record's timestamp with its admission's discharge timestamp.
        if entity == "discharge_records" and stamp(row, "discharge") != end:

            # Flag disagreeing discharge timestamps without guessing which is correct.
            errors.append("Discharge record timestamp disagrees with admission")

        # Check a follow-up appointment only when that optional date is present.
        if entity == "discharge_records" and row.get("follow_up_appointment"):

            # A follow-up appointment must not have a date before discharge.
            if end and row["follow_up_appointment"] < end.date().isoformat():

                # Record an invalid follow-up date relative to discharge.
                errors.append("Follow-up appointment precedes discharge")

    # Return distinct issues in sorted order so reports remain reproducible.
    return sorted(set(errors))


# Repeat relationship checks until rejected parents leave no accepted children orphaned.
def validate_relationships(entries, keys, foreign, schema):
    """Repeat until removing a parent cannot leave an accepted orphan."""

    # Repeat because removing a parent can invalidate children during the next pass.
    while True:

        # Prepare source-specific lookup dictionaries for currently eligible parent records.
        indexes = {source: {entity: {} for entity in schema} for source in task1.SOURCES}

        # Inspect records without combining identifiers from different sources.
        for entry in entries:

            # Only records without an earlier rejection or duplicate decision remain eligible.
            if entry["status"] is None:

                # Use standardized fields when checking parent references.
                row = entry["cleaned"]

                # Index the eligible record by its entity's source-local primary key.
                indexes[entry["source"]][entry["entity"]][row[keys[entry["entity"]]]] = row

        # Collect this pass's failures before changing the parent lookup dictionaries.
        rejected = []

        # Inspect records without combining identifiers from different sources.
        for entry in entries:

            # Only records without an earlier rejection or duplicate decision remain eligible.
            if entry["status"] is None:

                # Apply all relationship and chronology rules to this currently eligible record.
                errors = relationship_errors(entry["entity"], entry["cleaned"],
                                             indexes[entry["source"]], keys, foreign)

                # Schedule records with unresolved problems for quarantine.
                if errors:

                    # Keep each rejected record together with all reasons found in this pass.
                    rejected.append((entry, errors))

        # No new failures means the remaining accepted relationships are stable.
        if not rejected:

            # Stop once another pass would remove no records.
            return

        # Apply this pass's rejection decisions together after checking all records.
        for entry, errors in rejected:

            # Quarantine these records; the next pass will no longer treat them as parents.
            entry["status"], entry["reasons"] = "quarantined", errors


# Save only the cleaned data, required examples, quarantine and cleaning documentation.
def write_outputs(entries, schema, required):

    # Count each input record under one final outcome.
    totals = Counter()

    # Collect representative field changes rather than generating a full audit file.
    examples, seen_examples = [], Counter()

    # Keep accepted records separate for each source and entity.
    cleaned = {source: {entity: [] for entity in schema} for source in task1.SOURCES}

    # Preserve unresolved records with their original contents and reasons.
    with (OUTPUT / "quarantine.jsonl").open("w", encoding="utf-8") as quarantine:

        for entry in entries:

            # A record without a previous rejection or duplicate decision is accepted.
            entry["status"] = entry["status"] or "accepted"

            source, entity, status = entry["source"], entry["entity"], entry["status"]

            # Count duplicates separately so the cleaning summary reconciles with raw counts.
            totals[(source, entity, status)] += 1

            if status == "accepted":

                # Store the standardized record; its source is identified by its output folder.
                cleaned[source][entity].append(entry["cleaned"])

            elif status == "quarantined":

                # Save original/cleaned values, location and all unresolved reasons.
                quarantine.write(fingerprint({k: v for k, v in entry.items() if k != "changes"}) + "\n")

            # Choose up to two before/after examples for each field, action and outcome.
            for field, before, after, action in entry["changes"]:

                key = (source, entity, field, action, status)

                if seen_examples[key] < 2:

                    examples.append({
                        "source": source, "entity": entity,
                        "record_number": entry["record_number"], "field": field,
                        "before": fingerprint(before), "after": fingerprint(after),
                        "action": action, "record_outcome": status,
                    })

                    seen_examples[key] += 1

    # Summarize how many records were accepted, quarantined or removed as duplicates.
    summaries = []

    for source in task1.SOURCES:

        for entity in schema:

            counts = {state: totals[(source, entity, state)]
                      for state in ("accepted", "quarantined", "duplicate_removed")}

            summaries.append({"source": source, "entity": entity,
                              "input_records": sum(counts.values()), **counts})

            # Write one accepted CSV per entity within the source's folder.
            rows = cleaned[source][entity]

            timestamps = sorted({field for row in rows for field in row
                                 if field.endswith("_timestamp")})

            save_csv(OUTPUT / "cleaned" / source / f"{entity}.csv",
                     rows, list(schema[entity]) + timestamps)

    # Provide the required cleaning summary and representative before/after examples.
    save_csv(OUTPUT / "cleaning_summary.csv", summaries,
             ["source", "entity", "input_records", "accepted", "quarantined", "duplicate_removed"])

    save_csv(OUTPUT / "before_after_examples.csv", examples,
             ["source", "entity", "record_number", "field", "before", "after", "action", "record_outcome"])

    # Combine the per-entity results into overall counts for the documentation.
    grand = Counter()

    for row in summaries:

        grand.update({key: row[key] for key in
                      ("input_records", "accepted", "quarantined", "duplicate_removed")})

    # Document the cleaning rules and results required for Task 2.
    policies = {
        "record_counts": dict(grand),
        "required_fields": {entity: sorted(fields) for entity, fields in required.items()},
        "missing_markers": sorted(MISSING),
        "category_mappings": CATEGORIES,
        "numeric_screening_ranges": NUMBERS,
        "missing_value_policy": (
            "Documented markers become null. Literal 'None' in allergy/medication text is preserved. "
            "Optional missing values remain null; invalid optional numeric measurements become null. "
            "Missing required fields and other unresolved problems quarantine the record with reasons."
        ),
        "duplicate_policy": (
            "Within each source/entity, remove exact copies and identical standardized records sharing "
            "a local primary key. Quarantine all conflicting versions of the same key. Patients with "
            "the same insurance number and birth date but different IDs require review. Do not merge "
            "by name or by a shared ID across sources. Duplicate removals are counted in the summary."
        ),
        "text_policy": (
            "Collapse whitespace; use title case for synthetic personal names except Japanese names. "
            "Preserve other clinical text capitalization. Apply explicit category mappings."
        ),
        "date_and_timezone_policy": (
            "Use each source's documented date format; reject ambiguous or impossible dates. "
            "Output ISO dates and HH:MM:SS times. No source supplies a time zone: preserve local "
            "wall times, do not assume UTC offsets, and compare chronology within each source only."
        ),
        "numeric_and_unit_policy": (
            "Convert numeric types; enforce documented integer/range rules. Convert Fahrenheit to "
            "Celsius rounded to one decimal. Do not guess missing units or invent measurements. "
            "Retain diagnostic reference-unit because no physical conversion is documented."
        ),
        "clinical_category_policy": (
            "Use the explicit mappings above. Triage priorities use the same integer scale 1-5 in all "
            "sources. The revised synthetic sources explicitly supply admission types, mapped to "
            "Emergency or Elective independently of Open/Closed admission status, with explicit admission-source labels. The cleaner never "
            "infers a missing type; missing required or unknown types require quarantine."
        ),
        "relationship_and_chronology_policy": (
            "Validate references against accepted parents, patient/admission agreement, unit/order "
            "links and event chronology. Quarantine unresolved records; repeat reference checking "
            "after parent removals so no accepted children reference quarantined parents."
        ),
        "output_policy": (
            "Accepted CSV files are grouped by source; empty cells represent null. The example file "
            "contains representative changes. Quarantine retains original and standardized records "
            "with reasons. Raw source files are read only and are never rewritten by this script."
        ),
    }

    # Save the documented rules alongside the cleaning results.
    (OUTPUT / "cleaning_rules_and_results.json").write_text(
        json.dumps(policies, ensure_ascii=False, indent=2), encoding="utf-8")

    return dict(grand)



# Coordinate loading, normalization, duplicate handling, validation and final reporting.
def main():

    # Create the Task 2 output directory when needed.
    OUTPUT.mkdir(exist_ok=True)

    # Load field mappings, primary keys, relationships and required-field rules.
    schema, keys, foreign, required = read_schema()


    # Read all four original formats using Task 1's parsers.
    sources = load_sources(schema)

    # Keep each original record together with its cleaned values and audit details.
    entries = []

    # Process each independent hospital source separately.
    for source, tables in sources.items():

        # Retrieve an entity's loaded records and original input locations.
        for entity, (rows, locations, _, _, _) in tables.items():

            # Pair records with locations and assign one-based source record numbers.
            for number, (raw, location) in enumerate(zip(rows, locations), 1):

                # Normalize one record and collect unresolved issues and field changes.
                cleaned, errors, changes = normalize(source, entity, raw, schema, required)

                # Preserve provenance and original values; local failures begin in quarantine.
                entries.append({"source": source, "entity": entity, "record_number": number,
                                "location": location, "original": raw, "cleaned": cleaned,
                                "reasons": errors, "status": "quarantined" if errors else None, "changes": changes})

    # Remove confirmed extra copies and flag conflicting or uncertain entity matches.
    find_duplicates(entries, keys)

    # Resolve reference and chronology failures, including cascading parent removals.
    validate_relationships(entries, keys, foreign, schema)

    # Write the cleaned data, quarantine, required examples and cleaning documentation.
    result = write_outputs(entries, schema, required)



    # Make the final counts available to callers as a Python dictionary.
    return result


# Start the pipeline only when this file is executed directly, not when imported.
if __name__ == "__main__":

    main()
