from cde_recommend.schema import CLOSEST_MATCHES_SCHEMA, build_strict_schema


def test_enforce_object_rules_adds_required_and_additional_properties():
    # Given: a plain object schema without strict-mode fields
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
    }
    assert "additionalProperties" not in schema

    # When: strict schema is built
    result = build_strict_schema(schema)

    # Then: required and additionalProperties are added
    assert result["additionalProperties"] is False
    assert sorted(result["required"]) == ["age", "name"]


def test_enforce_nested_objects():
    # Given: an object schema with a nested object property
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

    # When: strict schema is built
    result = build_strict_schema(schema)

    # Then: nested objects also get strict-mode fields
    inner = result["properties"]["inner"]
    assert inner["additionalProperties"] is False
    assert inner["required"] == ["value"]


def test_enforce_array_items():
    # Given: an array schema whose items are objects
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
            },
        },
    }

    # When: strict schema is built
    result = build_strict_schema(schema)

    # Then: array item objects also get strict-mode fields
    assert result["items"]["additionalProperties"] is False
    assert result["items"]["required"] == ["id"]


def test_built_schema_is_strict():
    # Given: the pre-built ClosestMatchesIndex schema

    # When/Then: it has strict-mode fields at the top level
    assert CLOSEST_MATCHES_SCHEMA["additionalProperties"] is False
    assert "required" in CLOSEST_MATCHES_SCHEMA
    assert "closest_matches" in CLOSEST_MATCHES_SCHEMA["required"]
