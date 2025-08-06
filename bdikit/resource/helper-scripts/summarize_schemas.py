#!/usr/bin/env python3
"""
Summarize the contents of all_schemas_combined.json

For each top‑level key print:
  • total CDEs
  • how many have permissible_values
  • total permissible_values across all its CDEs
"""

import json
from pathlib import Path

def main():
    combined_path = Path("all_schemas_combined.json")
    if not combined_path.is_file():
        raise FileNotFoundError("all_schemas_combined.json not found in the current directory")

    with combined_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\nFound {len(data)} top‑level groups in {combined_path.name}:\n")

    for group_name, cdes in data.items():
        total_cdes = len(cdes)
        with_perm = sum(1 for v in cdes.values() if v.get("permissible_values"))
        total_perm_vals = sum(len(v.get("permissible_values", [])) for v in cdes.values())

        print(
            f"• {group_name}\n"
            f"    CDEs: {total_cdes}\n"
            f"    CDEs with permissible_values: {with_perm}\n"
            f"    Total permissible_values: {total_perm_vals}\n"
        )

if __name__ == "__main__":
    main()
