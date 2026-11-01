import pytest

from skypoints.parse import PipelineError, file_date_from_name, parse_member_file


def test_file_date(tmp_path):
    assert str(file_date_from_name("SKYPOINTS_MEMBERS_20240115.txt")) == "2024-01-15"
    with pytest.raises(PipelineError):
        file_date_from_name("members.txt")


def test_columns_found_by_name_not_position(tmp_path):
    p = tmp_path / "SKYPOINTS_MEMBERS_20240115.txt"
    p.write_text("H|Country|Member_Id|Member_Name|Enrollment_Date\nD|USA|1|Ann|20200101\n")
    rows, rejects, _ = parse_member_file(p)
    assert rows[0]["member_id"] == "1" and rows[0]["country"] == "USA" and rows[0]["post_code"] is None


def test_bad_lines_are_rejected_not_fatal(make_members):
    p = make_members("20240115", "D|A|1|20200101|||||||", "X|junk", "D|short|2")
    rows, rejects, _ = parse_member_file(p)
    assert [r.reason for r in rejects] == ["unknown_record_type", "column_count_mismatch"]


def test_missing_mandatory_column_stops_run(tmp_path):
    p = tmp_path / "SKYPOINTS_MEMBERS_20240115.txt"
    p.write_text("H|Member_Name|Country\nD|A|US\n")
    with pytest.raises(PipelineError):
        parse_member_file(p)
