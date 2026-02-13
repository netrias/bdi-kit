from cde_recommend.schema import CLOSEST_MATCHES_SCHEMA, build_strict_schema


def test_enforce_object_rules_adds_required_and_additional_properties():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
    }
    result = build_strict_schema(schema)

    assert result["additionalProperties"] is False
    assert sorted(result["required"]) == ["age", "name"]


def test_enforce_nested_objects():
    schema = {
        "type": "object",
        "properties": {
            "inner": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                },
            },
        },
    }
    result = build_strict_schema(schema)

    inner = result["properties"]["inner"]
    assert inner["additionalProperties"] is False
    assert inner["required"] == ["value"]


def test_enforce_array_items():
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
            },
        },
    }
    result = build_strict_schema(schema)

    assert result["items"]["additionalProperties"] is False
    assert result["items"]["required"] == ["id"]


def test_built_schema_is_strict():
    # The pre-built schema should have all objects with additionalProperties=False
    assert CLOSEST_MATCHES_SCHEMA["additionalProperties"] is False
    assert "required" in CLOSEST_MATCHES_SCHEMA
    assert "closest_matches" in CLOSEST_MATCHES_SCHEMA["required"]
