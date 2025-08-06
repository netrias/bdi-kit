#!/usr/bin/env python3
"""
To make the introspection endpoints work we need to have a file that shows the full schemas
of each of the data models we handle. So within each data model key will be a dictionary showing
the CDEs, a description for each CDE, and any permissible values if it may have.

This scrip generates this combined file. 

It is followed up by a script in the zero-shot repo that will assign each CDE a unique id number so we can have another 
cde_id to cde name mappings file, also used by one of the introspection endpoints.
"""

import json
from pathlib import Path

# ------------------------------------------------------------------
# EDIT THIS LIST with the files you want to include (any order)
#    They can be absolute paths or paths relative to this script.
files_to_merge = [
    "../ccdi_schema.json",
    "../cds_schema.json",
    "../gc_schema.json",
    "../sage_ChIPSeqTemplate_schema.json",
    "../sage_ClinicalAssayTemplate_schema.json",
    "../sage_ImagingAssayTemplate_schema.json",
    "../sage_RNASeqTemplate_schema.json",
]
# ------------------------------------------------------------------

def transform_entry(entry: dict) -> dict:
    """
    Convert one CDE entry:
      - column_description ➜ cde_description
      - value_data ➜ permissible_values (list of keys)
    """
    return {
        "cde_description": entry.get("column_description", ""),
        "permissible_values": list(entry.get("value_data", {}).keys())
    }

def load_and_transform(path: Path) -> dict:
    """Load a single file and apply the transform to every top-level key."""
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    return {k: transform_entry(v) for k, v in raw.items()}

def main(file_list):
    combined = {}

    for file_name in file_list:
        path = Path(file_name).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Cannot find: {path}")

        key = path.stem          # filename without extension
        combined[key] = load_and_transform(path)

    # Write out if you want a file on disk
    out_path = Path("all_schemas_combined.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)
    print(f"Combined JSON written to {out_path}")

    return combined

if __name__ == "__main__":
    merged = main(files_to_merge)

