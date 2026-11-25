"""Task 1: load and profile TXT, CSV, XML and JSON. No extra packages needed."""

from collections import Counter

import csv

from datetime import datetime

import json

import math

from pathlib import Path

import re

import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent

# Use the revised synthetic snapshot; the original raw folder remains unchanged.
# Run prepare_admission_types.py first to reproduce this source version.
RAW = BASE / "uncleaned data" / "raw_with_admission_types"

OUTPUT = BASE / "task1_output"

"""describes where each source is and how its date are written"""

SOURCES = {

    "A": ("Source_A_North_America_Canada_TXT", "%Y-%m-%d"),

    "B": ("Source_B_Europe_Germany_CSV", "%d.%m.%Y"),

    "C": ("Source_C_Asia_Japan_XML", "%Y/%m/%d"),

    "D": ("Source_D_Africa_South_Africa_JSON", "%d/%m/%Y"),

}

"""describes where each source is and how its date are written"""

def log_error(log, source, path, location, reason, raw=None):

    log.write(json.dumps({"source": source, "file": str(path), "location": location,

                          "reason": str(reason), "raw": raw}, ensure_ascii=False) + "\n")

"""load table"""

def load_table(path, delimiter, source, log):

    # Initialize lists for valid records, their locations and column names

    rows, locations, fields = [], [], []

     # Initialize the rejected record counter and file completion status

    rejected, complete = 0, True

    try:

        # Open the file using UTF-8 encoding and preserve line endings

        with path.open(encoding="utf-8-sig", newline="") as file:

            reader = csv.reader(file, delimiter=delimiter, strict=True)

            # Extract the first record as the header

            # Return an empty list if the file is empty

            fields = next(reader, [])

            # Check for missing, blank or duplicate column names

            if not fields or any(not f.strip() for f in fields) or len(set(fields)) != len(fields):

                raise ValueError("Missing, blank or duplicate headers")

            for row in reader:

                # Check whether the number of values matches the number of columns

                if len(row) != len(fields):

                    rejected += 1

                    # Record the invalid row and the reason for its rejection

                    log_error(log, source, path, reader.line_num,

                              f"Expected {len(fields)} fields; got {len(row)}", row)

                else:

                    # Pair each column name with its corresponding value,

                    # convert the pairs into a dictionary and store the record

                    rows.append(dict(zip(fields, row)))

                    locations.append(f"ending at line {reader.line_num}")

    # Catch file access, encoding, parsing and validation errors

    except (OSError, UnicodeError, csv.Error, ValueError) as error:

         # Indicate that the file could not be completely processed

        complete = False

         # Stop processing and log the error affecting the unread remainder

        log_error(log, source, path, "file / unread remainder", error)

    return rows, locations, fields, rejected, complete

# prevents json object from containaing duplicate keys without reporting an error 

def unique_keys(pairs):

    """Prevent JSON duplicate keys from silently overwriting values."""

    result = {}

    for key, value in pairs:

        if key in result:

            raise ValueError(f"Duplicate JSON key: {key}")

        result[key] = value

    return result

#This function rejects nonstandard JSON numerical constants such as NaN

def reject_constant(value):

    raise ValueError(f"Invalid JSON constant: {value}")

#loads xml file and converts it into a python dictionary 

def load_nested(path, source, log):

    # Initialize a dictionary to store all extracted entities
    tables = {}

    try:
        # Check whether the source is an XML file
        if source == "C":

            # Parse the XML file and retrieve its root element
            root = ET.parse(path).getroot()

            # Verify that the root element has the expected name
            if root.tag != "hospital_dataset":
                raise ValueError("Expected hospital_dataset root")

            # Create a list of tuples containing each entity name
            # and its corresponding list of XML records
            groups = [(group.tag, list(group)) for group in root]

        # Otherwise, process the source as a JSON file
        else:

            # Open the JSON file using UTF-8 encoding
            with path.open(encoding="utf-8-sig") as file:

                # Convert the JSON document into Python objects,
                # while rejecting duplicate keys and invalid JSON constants
                document = json.load(file, object_pairs_hook=unique_keys,
                                     parse_constant=reject_constant)

            # Verify that both the JSON document and its entities
            # object are dictionaries
            if not isinstance(document, dict) or not isinstance(document.get("entities"), dict):
                raise ValueError("Expected an entities object")

            # Create a list of tuples containing each entity name
            # and its corresponding list of JSON records
            groups = list(document["entities"].items())

        # Iterate through each entity and its associated records
        for entity, records in groups:

            # Check whether the entity has already been processed
            # or whether its records are not stored in a list
            if entity in tables or not isinstance(records, list):
                raise ValueError(f"Repeated entity or invalid entity list: {entity}")

            # Initialize lists for valid records and their locations,
            # and initialize the rejected record counter
            rows, locations, rejected = [], [], 0

            # Iterate through each record and retrieve its index
            for index, record in enumerate(records):

                # Construct the original location of the record
                # using its entity name and index
                location = f"{entity}[{index}]"

                # Preserve the original record for error logging.
                # Convert XML elements into strings and keep JSON objects unchanged
                original = ET.tostring(record, encoding="unicode") if source == "C" else record

                # Perform XML-specific validation and conversion
                if source == "C":

                    # Extract the tag names of all child elements
                    # representing the record's fields
                    keys = [child.tag for child in record]

                    # Validate the XML record by ensuring that:
                    # 1. Its tag name is "record"
                    # 2. The record has no XML attributes
                    # 3. There are no duplicate field names
                    # 4. Each field has no nested elements or XML attributes
                    valid = (record.tag == "record" and not record.attrib
                             and len(keys) == len(set(keys))
                             and all(not len(child) and not child.attrib for child in record))

                    # Convert a valid XML record into a dictionary,
                    # using child tags as keys and child text as values.
                    # Assign None if the record is invalid
                    record = {child.tag: child.text for child in record} if valid else None

                # Validate both XML and JSON records by checking whether:
                # 1. The record is not a dictionary
                # 2. The record is empty
                # 3. Any field contains a nested dictionary or list
                if (not isinstance(record, dict) or not record
                        or any(isinstance(v, (dict, list)) for v in record.values())):

                    # Increment the rejected record counter
                    rejected += 1

                    # Log the rejected record, its location and
                    # the reason for its rejection
                    log_error(log, source, path, location,
                              "Expected scalar record fields", original)

                else:

                    # Add the valid record to the list of extracted records
                    rows.append(record)

                    # Store the original location of the valid record
                    locations.append(location)

            # Iterate through all valid records and collect their field names.
            # Remove duplicate field names while preserving their order
            fields = list(dict.fromkeys(key for row in rows for key in row))

            # Store the entity's valid records, record locations,
            # unique field names, rejected record count and completion status
            tables[entity] = (rows, locations, fields, rejected, True)

    # Catch file access, character encoding, data validation
    # and XML parsing errors
    except (OSError, UnicodeError, ValueError, ET.ParseError) as error:

        # Log the error that prevented the document from being processed
        log_error(log, source, path, "file", error)

        # Return an empty dictionary to indicate document extraction failure
        return {}

    # Return the dictionary containing all successfully extracted entities
    return tables

# convert field names into lower case with underscore
def field_name(field):

    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", field).lower()

#checks whether a value counts as missing
def missing(value, field):

    # Source documentation defines these markers as missing in all fields.
    # Literal "None" in allergy/medication text describes absence and is preserved.
    tokens = {"", "NULL", "N/A", "NAN", "NA", "K.A.", "未記録", "-"}

    return value is None or (isinstance(value, str) and value.strip().upper() in tokens)

#checks whether a value can be interpreted as a finite number.
def numeric(value):

    try:

        return not isinstance(value, bool) and math.isfinite(float(value))

    except (TypeError, ValueError, OverflowError):

        return False

#checks whether a value can be interpreted as a date or time using a specified format.
def parses(value, pattern):

    try:

        datetime.strptime(str(value).strip(), pattern)

        return True

    except ValueError:

        return False

# examines the values of a column and determines what data type they represent.
def infer_type(field, values, date_format):

    if not values:

        return "unknown (all missing)"

    name = field_name(field)

    if (name.endswith(("_id", "_nr", "_number")) or "code" in name

            or name in {"icd9", "room", "ward"}):

        return "identifier/code (keep as string)"

    if all(isinstance(v, bool) for v in values):

        return "boolean"

    if all(parses(v, date_format) for v in values):

        return "date"

    # German time fields use dots. Check named time fields before numeric inference
    # so a valid value such as "08.00" is not mistaken for the number 8.
    if name.endswith("_time"):

        patterns = ("%H.%M", "%H.%M.%S") if date_format == "%d.%m.%Y" else ("%H:%M", "%H:%M:%S")

        return "time" if all(any(parses(v, pattern) for pattern in patterns) for v in values) else "text or mixed values"

    if all(numeric(v) for v in values):

        return "integer" if all(float(v).is_integer() for v in values) else "decimal"

    return "text or mixed values"

# checking whether an individual field value is valid according to specific data-quality rules and returning an explanation if it is invalid.
def invalid_reason(field, value, row, date_format):

    name = field_name(field)

    if name.endswith("_date") or name in {"date_of_birth", "date_of_death", "aufnahme_datum", "follow_up_appointment"}:

        if not parses(value, date_format):

            return f"Invalid date; expected {date_format}"

    elif name.endswith("_time"):

        # Validate the source's actual time notation without changing the raw value.
        patterns = ("%H.%M", "%H.%M.%S") if date_format == "%d.%m.%Y" else ("%H:%M", "%H:%M:%S")

        if not any(parses(value, f) for f in patterns):

            return "Invalid time"

    elif name in {"body_temperature", "body_temp", "temp_reading"}:

        unit = next((v for k, v in row.items() if field_name(k) == "temperature_unit"), "")

        limits = {"C": (25, 45), "F": (77, 113)}.get(str(unit).strip().upper())

        if not numeric(value) or not limits or not limits[0] <= float(value) <= limits[1]:

            return "Invalid temperature (screening: 25-45 C or 77-113 F)"

    elif name in {"oxygen_saturation", "pain_level", "heart_rate", "respiratory_rate"}:

        low, high = {"oxygen_saturation": (0, 100), "pain_level": (0, 10),

                     "heart_rate": (1, 300), "respiratory_rate": (1, 100)}[name]

        if not numeric(value) or not low <= float(value) <= high:

            return f"Invalid numeric value; screening range {low}-{high}"

    return ""

#generate the profiling reports entity_profile.csv field_profile.csv quality_issues.csv
def save_csv(name, rows, columns):

    with (OUTPUT / name).open("w", encoding="utf-8-sig", newline="") as file:

        writer = csv.DictWriter(file, fieldnames=columns)

        writer.writeheader()

        writer.writerows(rows)

# Main function that coordinates the extraction and initial profiling of all four hospital datasets.
# Loads TXT, CSV, XML and JSON files, stores the extracted records,
# analyzes entities and fields, detects duplicates, missing values and invalid data,
# generates profiling reports and an ingestion error log, and returns all extracted data.
def main():

    OUTPUT.mkdir(exist_ok=True)

    data, counts, profiles, issues = {}, [], [], []

    with (OUTPUT / "ingestion_errors.jsonl").open("w", encoding="utf-8") as log:

        for source, (folder, date_format) in SOURCES.items():

            directory = RAW / folder

            if source in {"A", "B"}:

                extension, delimiter = ("txt", "|") if source == "A" else ("csv", ",")

                files = sorted(directory.glob(f"*.{extension}"))

                if not files:

                    log_error(log, source, directory, "folder", "No input files found")

                tables = {p.stem: load_table(p, delimiter, source, log) for p in files}

            else:

                path = directory / ("hospital.xml" if source == "C" else "hospital.json")

                tables = load_nested(path, source, log)

            data[source] = {}

            for entity, (rows, locations, fields, rejected, complete) in tables.items():

                data[source][entity] = rows  # One list of dictionaries per entity.

                duplicates = Counter(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)

                counts.append({"source": source, "entity": entity, "records": len(rows),

                               "exact_duplicate_extras": sum(n - 1 for n in duplicates.values()),

                               "rejected_malformed": rejected, "read_complete": complete})

                for field in fields:

                    values = [row.get(field) for row in rows]

                    present = [v for v in values if not missing(v, field)]

                    profiles.append({"source": source, "entity": entity, "field": field,

                                     "inferred_type": infer_type(field, present, date_format),

                                     "missing_count": len(values) - len(present),

                                     "examples": json.dumps(list(dict.fromkeys(present))[:3], ensure_ascii=False)})

                    for index, value in enumerate(values):

                        if missing(value, field):

                            continue

                        reason = invalid_reason(field, value, rows[index], date_format)

                        if isinstance(value, str) and value != value.strip():

                            reason += "; Leading/trailing whitespace"

                        if reason:

                            issues.append({"source": source, "entity": entity, "location": locations[index],

                                           "field": field, "value": value, "reason": reason})


    save_csv("entity_profile.csv", counts, ["source", "entity", "records", "exact_duplicate_extras", "rejected_malformed", "read_complete"])

    save_csv("field_profile.csv", profiles, ["source", "entity", "field", "inferred_type", "missing_count", "examples"])

    save_csv("quality_issues.csv", issues, ["source", "entity", "location", "field", "value", "reason"])



    return data


if __name__ == "__main__":

    data = main()
