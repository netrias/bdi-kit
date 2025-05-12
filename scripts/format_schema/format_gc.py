import json
from os.path import join, dirname

# Set where we load the raw GC data model from
RAW_GC_PATH = join(dirname(__file__), "GC_Dictionary_All_v6.0.4_raw_schema.json")
# Set where we save the GC data model in the format bdi-kit expects
FORMATTED_GC_PATH = join(dirname(__file__), "../../bdikit/resource/gc_schema.json")

# List of keys that we want to get properties for from the data model
nodes = [
    "program",
    "study",
    "participant",
    "diagnosis",
    "treatment",
    "sample",
    "file",
    "genomic_info",
    "image",
    "MultiplexMicroscopy",
    "NonDICOMCTimages",
    "NonDICOMMRimages",
    "NonDICOMpathologyImages",
    "NonDICOMPETimages",
    "NonDICOMradiologyAllModalities",
    "proteomic",
]

# Dict to capture our desired form of the data model
metadata = {}

# Load the json file
with open(RAW_GC_PATH, encoding="utf-8") as json_file:
    gc_schema = json.load(json_file)

# For each node that we care about
for node in nodes:
    # Get the relevant key/value pairs from each property in this node and add them to the metadata dict
    
    # Get all the properties for this node, if none, something wrong, break
    properties = gc_schema.get(node, [])
    if not isinstance(properties, list):
        print("Error Stopping")
        break         
    
    # Loop through all the properties we just got
    for prop in properties:
        # Make sure a poperty has the key "Property"
        if isinstance(prop, dict) and "Property" in prop:
            
            # Get the acceptable values
            enums = prop.get('Acceptable Values', [])
            enum_dict = {key: "" for key in enums} # Format them

            # Add an entry in our metadata dict for this property
            metadata[prop["Property"]] = {
                "column_description": prop.get("Description", ""),
                "value_data": enum_dict
            }

with open(FORMATTED_GC_PATH, "w") as f:
    json.dump(metadata, f, indent=4)

print("GC schema formatted successfully.")
print(f'number of properties: {len(metadata)}')
