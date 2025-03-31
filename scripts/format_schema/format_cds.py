
import json
import yaml
from os.path import join, dirname

# Set where we load the raw CDS data model from
RAW_CDS_PATH = join(dirname(__file__), "./cds-model-props-5_0_2_raw.yml")
# Set where we save the cds data model in the format bdi-kit expects
FORMATTED_CDS_PATH = join(dirname(__file__), "../../bdikit/resource/cds_schema.json")

# Dict to capture our desired form of the data model
metadata = {}


# Load the YAML file
with open(RAW_CDS_PATH, 'r') as yml_file:
    cds_schema = yaml.safe_load(yml_file)

# Extract the PropDefinitions dictionary, which contains all the common data elements (CDEs)
prop_definitions = cds_schema.get('PropDefinitions', {})

# Iterate over each CDE in PropDefinitions
for cde, details in prop_definitions.items():
    # Get the CDE name
    metadata[cde] = {}

    # Get the CDE's description
    cde_description = details.get("Desc", "")
    metadata[cde]["column_description"] = cde_description

    # Add the permissible values (PVs) (ie. what bdi-kit calls value data)
    # Note: there are no descriptions of the PVs in the CDS data model/schema file
    enums = details.get('Enum', [])
    # Create a new dictionary where each element from enums becomes a key and is associated with an empty string 
    enum_dict = {key: "" for key in enums}
    # Add this dict as a value to the value_data key
    metadata[cde]["value_data"] = enum_dict

with open(FORMATTED_CDS_PATH, "w") as f:
    json.dump(metadata, f, indent=4)

print("CDS schema formatted successfully.")