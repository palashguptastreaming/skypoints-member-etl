from datetime import date

import pytest

from skypoints import checks, staging
from skypoints.parse import file_date_from_name, parse_member_file


def stage(con, path):
    """Parse a member file, load raw, stage it, and return the warnings."""
    rows, rejects, header = parse_member_file(path)
    staging.load_raw(con, path.name, file_date_from_name(path), rows)
    staging.quarantine_rejects(con, "member_file", path.name, rejects)
    staging.stage_members(con, path.name, file_date_from_name(path))
    staging.reconcile(con, path.name)
    return checks.collect_warnings(con, path.name, header)


def q(con, sql):
    return con.execute(sql).fetchall()


def test_age_and_stale_member(con, make_members):
    p = make_members("20240115",
                     "D|A|1|20200101|20231001|GLD||NY|USA|15011990|A",   # birthday today -> 34, 106 days -> stale
                     "D|B|2|20200101|20231220|GLD||NY|USA|16011990|A")   # birthday tomorrow -> 33, 26 days -> fresh
    stage(con, p)
    assert q(con, "SELECT member_id, age, stale_member FROM stg_member ORDER BY 1") == [("1", 34, True), ("2", 33, False)]


def test_exactly_90_days_is_not_stale(con, make_members):
    p = make_members("20240115", "D|A|1|20200101|20231017|GLD||NY|USA|15011990|A")   # 20231017 -> 90 days
    stage(con, p)
    assert q(con, "SELECT stale_member FROM stg_member") == [(False,)]


def test_country_is_standardised(con, make_members):
    p = make_members("20240115", *[f"D|N{i}|{i}|20200101|||||{c}||" for i, c in
                                   enumerate(["USA", "ind", "PHIL", "Canada", "AU"], 1)])
    stage(con, p)
    assert [r[0] for r in q(con, "SELECT country_iso2 FROM stg_member ORDER BY member_id")] == ["US", "IN", "PH", "CA", "AU"]


def test_bad_rows_go_to_quarantine_with_reason(con, make_members):
    p = make_members("20240115", "D||1|20200101||||XX|USA||", "D|A||20200101||||XX|USA||",
                     "D|A|2|bad||||XX|USA||", "D|A|3|20200101||||XX|MARS||",
                     "D|First|4|20200101||||NY|USA||", "D|Second|4|20200102||||NY|USA||")
    stage(con, p)
    assert sorted(r[0] for r in q(con, "SELECT reason FROM quarantine")) == [
        "duplicate_member_in_file", "invalid_enrollment_date", "missing_member_id",
        "missing_member_name", "unknown_or_missing_country"]
    assert q(con, "SELECT member_name FROM stg_member") == [("Second",)]          # last row in the file wins


def test_field_too_long_is_quarantined(con, make_members):
    p = make_members("20240115", "D|A|" + "9" * 19 + "|20200101||||NY|USA||")      # member id limit is 18
    stage(con, p)
    assert q(con, "SELECT reason FROM quarantine") == [("field_exceeds_max_length",)]


def test_null_text_and_blanks_become_missing(con, make_members):
    p = make_members("20240115", "D|A|1|20200101|NULL|N/A||NY|USA|NULL|A")
    stage(con, p)
    assert q(con, "SELECT last_flight_date, tier_code, dob, age, stale_member FROM stg_member") == [(None,) * 5]


def test_dob_leading_zero_is_repaired_with_a_warning(con, make_members):
    p = make_members("20240115", "D|A|1|20200101||||NY|USA|3051985|A")          # 3051985 -> 03051985
    warnings = stage(con, p)
    assert q(con, "SELECT dob FROM stg_member") == [(date(1985, 5, 3),)]
    assert "dob_leading_zero_repaired" in {w[0] for w in warnings}


def test_reconciliation_catches_lost_rows(con, make_members):
    p = make_members("20240115", "D|A|1|20200101||||NY|USA||", "D|B|2|20200101||||NY|USA||")
    stage(con, p)
    con.execute("DELETE FROM stg_member WHERE member_id = '2'")
    with pytest.raises(staging.ReconciliationError):
        staging.reconcile(con, p.name)


def test_warnings(con, make_members):
    p = make_members("20240115", *[f"D|N{i}|{n}|20200101|||||USA|03051985|Z" for i, n in
                                   enumerate(["111111", "222222", "333333", "44"], 1)])
    codes = {w[0] for w in stage(con, p)}
    assert {"dominant_dob", "member_id_length_outlier", "unknown_active_flag", "missing_optional_column"} <= codes