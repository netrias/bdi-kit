import json

def count_json_keys(json_file_path):
    # Open and read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    # Count the number of top-level keys
    key_count = len(data.keys())
    
    print(f"Number of top-level keys: {key_count}")
    # print("Keys:")
    # for key in data.keys():
    #     print(f"- {key}")

# Example usage
if __name__ == "__main__":
    json_file_path = "sage_ClinicalAssayTemplate_schema.json"  # Replace with your file path
    count_json_keys(json_file_path)
