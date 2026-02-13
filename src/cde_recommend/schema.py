"""JSON schema enforcement for OpenAI structured output. Changes when the output format changes."""

from cde_recommend.types import ClosestMatchesIndex


def build_strict_schema(schema: dict) -> dict:
    """Recursively add required/additionalProperties for OpenAI strict mode compliance."""
    if not isinstance(schema, dict):
        return schema

    if schema.get("type") == "object":
        schema.setdefault("additionalProperties", False)
        props = schema.get("properties", {})
        if isinstance(props, dict):
            schema["required"] = sorted(props.keys())
        for v in props.values():
            build_strict_schema(v)
    elif schema.get("type") == "array" and "items" in schema:
        build_strict_schema(schema["items"])

    if "$defs" in schema and isinstance(schema["$defs"], dict):
        for v in schema["$defs"].values():
            build_strict_schema(v)

    return schema


CLOSEST_MATCHES_SCHEMA = build_strict_schema(ClosestMatchesIndex.model_json_schema())

TEXT_FORMAT_CONFIG: dict[str, object] = {
    "format": {
        "type": "json_schema",
        "name": "ClosestMatchesIndex",
        "strict": True,
        "schema": CLOSEST_MATCHES_SCHEMA,
    },
    "verbosity": "low",
}
