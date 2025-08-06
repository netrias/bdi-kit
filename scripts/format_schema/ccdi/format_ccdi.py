
import json
import yaml
from os.path import join, dirname

# Set where we load the raw CCDI data model from
RAW_DATA_PATH = join(dirname(__file__), "./ccdi-model-props.yml")
# Set where we save the CCDI data model in the format bdi-kit expects
FORMATTED_DATA_PATH = join(dirname(__file__), "../../../bdikit/resource/ccdi_schema.json")

# Dict to capture our desired form of the data model
data_model = {}

# Load the YAML file
with open(RAW_DATA_PATH, 'r') as yml_file:
    input_schema = yaml.safe_load(yml_file)

# Extract the PropDefinitions dictionary, which contains all the common data elements (CDEs)
prop_definitions = input_schema.get('PropDefinitions', {})

# Iterate over each CDE in PropDefinitions
for cde, details in prop_definitions.items():
    # Get the CDE name
    data_model[cde] = {}

    # Get the CDE's description
    cde_description = details.get("Desc", "")
    data_model[cde]["column_description"] = cde_description

    # Add the permissible values (PVs) (ie. what bdi-kit calls value data)
    enums = details.get('Enum', [])
    # Create a new dictionary where each element from enums becomes a key and is associated with an empty string 
    enum_dict = {key: "" for key in enums}
    # Add this dict as a value to the value_data key
    data_model[cde]["value_data"] = enum_dict

with open(FORMATTED_DATA_PATH, "w") as f:
    json.dump(data_model, f, indent=4)

print("Schema formatted successfully.")