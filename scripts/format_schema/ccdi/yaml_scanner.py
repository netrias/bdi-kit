# find_yaml_list_keys.py
import argparse
from typing import Any, List, Tuple
from collections import Counter
import yaml

def find_list_keys(obj: Any, min_len: int = 2, path: List[str] | None = None) -> List[Tuple[str, list]]:
    if path is None:
        path = []
    hits: List[Tuple[str, list]] = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and len(v) >= min_len:
                hits.append((".".join(path + [str(k)]), v))
            hits.extend(find_list_keys(v, min_len=min_len, path=path + [str(k)]))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            hits.extend(find_list_keys(item, min_len=min_len, path=path + [str(i)]))

    return hits

def main():
    ap = argparse.ArgumentParser(description="Find YAML keys whose values are lists of at least N items.")
    ap.add_argument("yaml_file", help="Path to the YAML file")
    ap.add_argument("--min-len", type=int, default=2, help="Only report lists with length >= this value (default: 2)")
    args = ap.parse_args()

    with open(args.yaml_file, "r") as f:
        data = yaml.safe_load(f)

    hits = find_list_keys(data, min_len=args.min_len)

    # 1) Print matching paths
    for p, v in hits:
        print(f"{p}  (len={len(v)})")

    if not hits:
        print("No lists meeting the length threshold were found.")
        return

    # 2) Unique key names (last segment of path)
    last_segments = [p.split(".")[-1] for p, _ in hits]
    unique_names = sorted(set(last_segments))
    print("\nUnique key names that have list values (filtered):")
    print(", ".join(unique_names))

    # 3) Count of unique key names
    print(f"\nCount of unique key names: {len(unique_names)}")

    # 4) Occurrences per key name
    counts = Counter(last_segments)
    print("\nOccurrences by key name:")
    for name, cnt in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"- {name}: {cnt}")

    # (optional) Totals
    print(f"\nTotal list-valued nodes matched: {len(hits)}")

if __name__ == "__main__":
    main()
