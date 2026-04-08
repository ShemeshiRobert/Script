from validator import validate_records


def _record(name: str = "Alice Smith", description: str = "CTO") -> dict[str, str]:
    return {"id": "abc", "name": name, "email": "", "description": description, "photoUrl": "", "Bio": ""}


class TestValidateRecords:
    def test_valid_records_return_no_errors(self):
        records = [_record(), _record(name="Bob Jones", description="Engineer")]
        assert validate_records(records) == []

    def test_empty_name_is_flagged(self):
        errors = validate_records([_record(name="")])
        assert len(errors) == 1
        assert errors[0].field == "name"

    def test_whitespace_only_name_is_flagged(self):
        errors = validate_records([_record(name="   ")])
        assert len(errors) == 1
        assert errors[0].field == "name"

    def test_empty_description_is_flagged(self):
        errors = validate_records([_record(description="")])
        assert len(errors) == 1
        assert errors[0].field == "description"

    def test_whitespace_only_description_is_flagged(self):
        errors = validate_records([_record(description="\t\n")])
        assert len(errors) == 1
        assert errors[0].field == "description"

    def test_both_fields_missing_yields_two_errors(self):
        errors = validate_records([_record(name="", description="")])
        fields = {e.field for e in errors}
        assert fields == {"name", "description"}

    def test_row_number_is_one_based(self):
        errors = validate_records([_record(), _record(name="")])
        assert errors[0].row == 2

    def test_errors_across_multiple_records_are_all_reported(self):
        records = [
            _record(name=""),
            _record(),
            _record(description=""),
        ]
        assert len(validate_records(records)) == 2

    def test_empty_input_returns_no_errors(self):
        assert validate_records([]) == []

    def test_missing_fields_treated_as_empty(self):
        # Records missing the key entirely (e.g. sparse dicts) should be flagged.
        errors = validate_records([{"id": "x"}])
        fields = {e.field for e in errors}
        assert fields == {"name", "description"}

    def test_error_contains_reason(self):
        errors = validate_records([_record(name="")])
        assert errors[0].reason != ""
