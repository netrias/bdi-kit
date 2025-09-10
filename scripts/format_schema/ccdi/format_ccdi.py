import json
import yaml
from os.path import join, dirname
from typing import Any, Iterable, List

# Set where we load the raw CCDI data model from
RAW_DATA_PATH = join(dirname(__file__), "./ccdi-model-props.yml")
# Set where we save the CCDI data model in the format bdi-kit expects
FORMATTED_DATA_PATH = join(dirname(__file__), "./ccdi_schema.json")

# Dict to capture our desired form of the data model
data_model = {}

def _strings_from_iterable(values: Any) -> List[str]:
    """
    Best-effort extraction of strings from a list-like object that may contain
    scalars or small dicts. Returns [] if not list-like.
    """
    if not isinstance(values, list):
        return []
    out: List[str] = []
    for v in values:
        if isinstance(v, (str, int, float, bool)):
            out.append(str(v))
        elif isinstance(v, dict):
            # Heuristics in case enums are dicts; keep simple & conservative
            for k in ("Value", "value", "label", "name", "preferred_label"):
                if k in v and isinstance(v[k], str):
                    out.append(v[k])
                    break
    return out

def _unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

# Load the YAML file
with open(RAW_DATA_PATH, "r") as yml_file:
    input_schema = yaml.safe_load(yml_file)

# Extract the PropDefinitions dictionary, which contains all the common data elements (CDEs)
prop_definitions = input_schema.get("PropDefinitions", {})

# Iterate over each CDE in PropDefinitions
for cde, details in prop_definitions.items():
    data_model[cde] = {}

    # Description
    cde_description = details.get("Desc", "")
    data_model[cde]["column_description"] = cde_description

    # Collect permissible values from both Enum and Type.item_type
    enums = _strings_from_iterable(details.get("Enum", []))

    item_type_vals: List[str] = []
    type_block = details.get("Type", {})
    if isinstance(type_block, dict):
        item_type_vals = _strings_from_iterable(type_block.get("item_type", []))

    combined = _unique_preserve_order(enums + item_type_vals)

    # Map each PV to empty string as expected by bdi-kit
    data_model[cde]["value_data"] = {pv: "" for pv in combined}

# Write out
with open(FORMATTED_DATA_PATH, "w") as f:
    json.dump(data_model, f, indent=4, ensure_ascii=False)

print("Schema formatted successfully.")
