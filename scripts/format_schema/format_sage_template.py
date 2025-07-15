import json
from os.path import join, dirname

# Set where we load the raw CDS data model from
RAW_CDS_PATH = join(dirname(__file__), "sage_templates_v2/RNASeqTemplate-deref.json")
# Set where we save the CDS data model in the format bdi-kit expects
FORMATTED_CDS_PATH = join(dirname(__file__), "../../bdikit/resource/sage_RNASeqTemplate_schema.json")

# Dict to capture our desired form of the data model
metadata = {}

# Load the JSON Schema file
with open(RAW_CDS_PATH, 'r') as json_file:
    raw_input_schema = json.load(json_file)

# Extract the 'properties' dictionary
properties = raw_input_schema.get('properties', {})

# Iterate over each property (CDE) in the schema
for cde, details in properties.items():
    metadata[cde] = {}

    # Get the CDE's description
    cde_description = details.get("description", "")
    metadata[cde]["column_description"] = cde_description

    # Handle enums as value_data if present
    enums = details.get('enum', [])
    enum_dict = {val: "" for val in enums} if enums else {}
    metadata[cde]["value_data"] = enum_dict

# Save the reformatted schema
with open(FORMATTED_CDS_PATH, "w") as f:
    json.dump(metadata, f, indent=4)

print("Sage template formatted successfully.")
