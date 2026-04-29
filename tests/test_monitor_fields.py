"""Tests for the annotation → API field translation layer."""

import pytest

from monitor_fields import (
    ANNOTATION_TO_FIELD,
    MONITOR_FIELDS,
    SENSITIVE_FIELDS,
    FieldCoercionError,
    coerce,
)


class TestFieldMap:
    def test_every_field_has_unique_annotation_and_api_name(self):
        annotations = [ann for ann, _, _ in MONITOR_FIELDS]
        api_names = [api for _, api, _ in MONITOR_FIELDS]

        assert len(annotations) == len(set(annotations))
        assert len(api_names) == len(set(api_names))

    def test_every_field_has_a_known_kind(self):
        valid_kinds = {"str", "int", "bool", "list_str", "list_int", "list_map", "map_str"}
        for _, _, kind in MONITOR_FIELDS:
            assert kind in valid_kinds

    def test_sensitive_fields_are_in_field_map(self):
        api_names = {api for _, api, _ in MONITOR_FIELDS}
        for sensitive in SENSITIVE_FIELDS:
            assert sensitive in api_names

    def test_terraform_parity_covers_documented_fields(self):
        """Spot-check that the major Terraform-documented arguments are present."""
        api_names = {api for _, api, _ in MONITOR_FIELDS}
        expected = {
            "monitor_type", "paused", "http_method", "request_timeout",
            "request_body", "request_headers", "expected_status_codes",
            "required_keyword", "follow_redirects", "remember_cookies",
            "verify_ssl", "auth_username", "auth_password", "regions",
            "ip_version", "port", "proxy_host", "proxy_port",
            "check_frequency", "confirmation_period", "recovery_period",
            "email", "sms", "call", "push", "critical_alert", "team_wait",
            "policy_id", "expiration_policy_id", "monitor_group_id",
            "team_name", "ssl_expiration", "domain_expiration",
            "maintenance_from", "maintenance_to", "maintenance_timezone",
            "maintenance_days", "playwright_script", "scenario_name",
            "environment_variables",
        }
        missing = expected - api_names
        assert not missing, f"missing API fields: {missing}"


class TestCoerceStr:
    def test_passes_through_unchanged(self):
        assert coerce("k", "str", "anything") == "anything"


class TestCoerceInt:
    def test_parses_integer(self):
        assert coerce("k", "int", "42") == 42

    def test_strips_whitespace(self):
        assert coerce("k", "int", "  60  ") == 60

    def test_rejects_non_integer(self):
        with pytest.raises(FieldCoercionError):
            coerce("k", "int", "not-a-number")


class TestCoerceBool:
    @pytest.mark.parametrize("raw", ["true", "True", "TRUE", "1", "yes", "YES"])
    def test_truthy_values(self, raw):
        assert coerce("k", "bool", raw) is True

    @pytest.mark.parametrize("raw", ["false", "False", "0", "no", "NO"])
    def test_falsy_values(self, raw):
        assert coerce("k", "bool", raw) is False

    def test_rejects_unknown_value(self):
        with pytest.raises(FieldCoercionError):
            coerce("k", "bool", "maybe")


class TestCoerceListStr:
    def test_parses_json_array(self):
        assert coerce("k", "list_str", '["us","eu"]') == ["us", "eu"]

    def test_parses_comma_separated(self):
        assert coerce("k", "list_str", "us, eu, as") == ["us", "eu", "as"]

    def test_drops_empty_csv_entries(self):
        assert coerce("k", "list_str", "us, ,eu") == ["us", "eu"]

    def test_rejects_non_string_elements(self):
        with pytest.raises(FieldCoercionError):
            coerce("k", "list_str", '["us", 1]')


class TestCoerceListInt:
    def test_parses_json_array(self):
        assert coerce("k", "list_int", "[200,201]") == [200, 201]

    def test_parses_comma_separated(self):
        assert coerce("k", "list_int", "200, 201, 204") == [200, 201, 204]

    def test_rejects_mixed_types(self):
        with pytest.raises(FieldCoercionError):
            coerce("k", "list_int", '[200, "ok"]')

    def test_rejects_booleans_in_int_list(self):
        with pytest.raises(FieldCoercionError):
            coerce("k", "list_int", "[true, false]")


class TestCoerceListMap:
    def test_parses_request_headers(self):
        result = coerce("k", "list_map", '[{"name":"X-Token","value":"abc"}]')
        assert result == [{"name": "X-Token", "value": "abc"}]

    def test_rejects_non_object_elements(self):
        with pytest.raises(FieldCoercionError):
            coerce("k", "list_map", '["X-Token: abc"]')

    def test_rejects_invalid_json(self):
        with pytest.raises(FieldCoercionError):
            coerce("k", "list_map", "not json")


class TestCoerceMapStr:
    def test_parses_environment_variables(self):
        assert coerce("k", "map_str", '{"FOO":"bar"}') == {"FOO": "bar"}

    def test_rejects_non_string_values(self):
        with pytest.raises(FieldCoercionError):
            coerce("k", "map_str", '{"PORT": 80}')

    def test_rejects_array(self):
        with pytest.raises(FieldCoercionError):
            coerce("k", "map_str", '["FOO=bar"]')


class TestAnnotationLookup:
    def test_known_annotation_resolves(self):
        assert ANNOTATION_TO_FIELD["check-frequency"] == ("check_frequency", "int")
        assert ANNOTATION_TO_FIELD["regions"] == ("regions", "list_str")
        assert ANNOTATION_TO_FIELD["request-headers"] == ("request_headers", "list_map")

    def test_unknown_annotation_returns_none(self):
        assert ANNOTATION_TO_FIELD.get("not-a-field") is None
