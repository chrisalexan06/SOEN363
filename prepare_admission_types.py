"""Generate a revised, entirely fictional educational dataset from preserved raw inputs.
The revision plan explicitly defines synthetic attributes and scenarios; no clinical facts
are inferred or fabricated by the Task 2 cleaner. Run before Tasks 1 and 2.
"""
import csv
import json
import random
import shutil
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET
import data_ingestion_and_profiling as task1

BASE = Path(__file__).resolve().parent
ORIGINAL = BASE / "uncleaned data" / "raw"
REVISED = BASE / "uncleaned data" / "raw_with_admission_types"
LABELS = {
    "A": ("admission_id", "admission_type", "Emergency", "Elective"),
    "B": ("FallNr", "Aufnahmeart", "Notfall", "Geplant"),
    "C": ("encounterNumber", "admissionType", "緊急", "予定"),
    "D": ("ADM_ID", "ADM_TYPE", "EMERGENCY", "ELECTIVE"),
}
EMERGENCY_PROBABILITY = {"A": .7, "B": .5, "C": .6, "D": .4}
SOURCE_COLUMNS = dict(zip("ABCD", ["source_A_TXT", "source_B_CSV", "source_C_XML", "source_D_JSON"]))
NEW_FIELDS = {"admissions": ["admission_type", "admission_source"], "patients": ["date_of_death"],
              "clinical_notes": ["note_type", "note_contents"], "radiology_examinations": ["examination_id"]}
SOURCE_LABELS = {
    "A": ["Emergency Department", "Physician Referral", "Hospital Transfer"],
    "B": ["Notaufnahme", "Arztüberweisung", "Krankenhausverlegung"],
    "C": ["救急外来", "医師紹介", "転院"],
    "D": ["ED", "PHYSICIAN_REFERRAL", "HOSPITAL_TRANSFER"],
}
MISSING = {"A": "NA", "B": "k.A.", "C": "未記録", "D": None}

def admission_type(source, identifier):
    rng = random.Random(f"SOEN363-admission-type-{source}-{identifier}")
    return LABELS[source][2 if rng.random() < EMERGENCY_PROBABILITY[source] else 3]

def encode(field, value, source):
    if value is None or value == "":
        return MISSING[source]
    if field.endswith("_date") or field in {"date_of_birth", "date_of_death", "follow_up_appointment"}:
        return date.fromisoformat(value).strftime(task1.SOURCES[source][1])
    if field.endswith("_time"):
        return value.replace(":", ".") if source == "B" else value
    if field == "admission_source":
        return SOURCE_LABELS[source][SOURCE_LABELS["A"].index(value)]
    if field == "admission_type":
        return LABELS[source][2 if value == "Emergency" else 3]
    return value

def main():
    if ORIGINAL.resolve() == REVISED.resolve():
        raise ValueError("Original and revised folders must differ")
    plan = json.loads((BASE / "synthetic_revision_plan.json").read_text(encoding="utf-8"))
    aliases, keys = {}, {}
    with (BASE / "task2_field_mapping.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            aliases.setdefault(row["entity"], {})[row["canonical_field"]] = row
            if row["primary_key"] == "True":
                keys[row["entity"]] = row["canonical_field"]
    for source, (folder, _) in task1.SOURCES.items():
        origin, target = ORIGINAL / folder, REVISED / folder
        if not origin.is_dir():
            raise FileNotFoundError(origin)
        shutil.copytree(origin, target, dirs_exist_ok=True)
        column = SOURCE_COLUMNS[source]
        updates, additions = plan[source]["updates"], plan[source]["additions"]
        def revise(entity, rows):
            fields = aliases[entity]
            key = fields[keys[entity]][column]
            for row in rows:
                identifier = str(row[key]).strip()
                for field in NEW_FIELDS.get(entity, []):
                    row[fields[field][column]] = MISSING[source]
                if entity == "admissions":
                    row[fields["admission_type"][column]] = admission_type(source, identifier)
                if entity == "clinical_notes":
                    row[fields["note_type"][column]] = "Progress Note"
                    row[fields["note_contents"][column]] = "Synthetic clinical review and follow-up note."
                for field, value in updates.get(entity, {}).get(identifier, {}).items():
                    row[fields[field][column]] = encode(field, value, source)
            for record in additions.get(entity, []):
                rows.append({item[column]: encode(field, record.get(field), source)
                             for field, item in fields.items()})
            return rows
        if source in "AB":
            ext, delim = ("txt", "|") if source == "A" else ("csv", ",")
            for entity in aliases:
                path = target / f"{entity}.{ext}"
                with path.open(encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f, delimiter=delim, strict=True)
                    fields, rows = list(reader.fieldnames), list(reader)
                revised = revise(entity, rows)
                fields += [aliases[entity][field][column] for field in NEW_FIELDS.get(entity, [])
                           if aliases[entity][field][column] not in fields]
                with path.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fields, delimiter=delim)
                    writer.writeheader(); writer.writerows(revised)
        elif source == "C":
            path = target / "hospital.xml"
            tree = ET.parse(path)
            for group in tree.getroot():
                rows = [{child.tag: child.text for child in record} for record in group]
                for record in list(group):
                    group.remove(record)
                for row in revise(group.tag, rows):
                    record = ET.SubElement(group, "record")
                    for key, value in row.items():
                        ET.SubElement(record, key).text = None if value is None else str(value)
            ET.indent(tree, space="  ")
            tree.write(path, encoding="utf-8", xml_declaration=True)
        else:
            path = target / "hospital.json"
            document = json.loads(path.read_text(encoding="utf-8-sig"))
            for entity, rows in document["entities"].items():
                document["entities"][entity] = revise(entity, rows)
            path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Revised fictional sources generated; original raw files unchanged.")

if __name__ == "__main__":
    main()
