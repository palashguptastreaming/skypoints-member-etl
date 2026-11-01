"""End-to-end test: runs the whole pipeline on the sample files and checks the final state."""
from pathlib import Path

from skypoints import redemptions
from skypoints.pipeline import process_redemption_file, run

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"
FILES = sorted(SAMPLE.glob("SKYPOINTS_*"))


def q(con, sql):
    return con.execute(sql).fetchall()


def test_members_end_up_in_one_country_table_each():
    con, _ = run(":memory:", FILES)
    counts = {t[0]: q(con, f"SELECT count(*) FROM {t[0]}")[0][0] for t in
              q(con, "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'tgt_%'")}
    assert counts == {"tgt_member_us": 2, "tgt_member_ca": 2, "tgt_member_in": 1, "tgt_member_ph": 1, "tgt_member_au": 2}
    assert q(con, "SELECT country_iso2 FROM member_country_index WHERE member_id = '223457'") == [("CA",)]


def test_bad_member_rows_are_quarantined_with_reasons():
    con, _ = run(":memory:", FILES)
    assert q(con, "SELECT reason, count(*) FROM quarantine WHERE source = 'member_file' GROUP BY 1 ORDER BY 1") == [
        ("column_count_mismatch", 1), ("duplicate_member_in_file", 1), ("invalid_enrollment_date", 1),
        ("missing_member_id", 1), ("missing_member_name", 1), ("unknown_or_missing_country", 1)]


def test_sample_data_problems_raise_warnings():
    con, _ = run(":memory:", FILES)
    codes = {r[0] for r in q(con, "SELECT code FROM dq_warning")}
    assert {"missing_optional_column", "dominant_dob", "member_id_length_outlier", "dob_leading_zero_repaired"} <= codes


def test_stale_flag_follows_the_ninety_day_rule():
    con, _ = run(":memory:", FILES)
    assert q(con, "SELECT member_id, stale_member FROM tgt_member_us ORDER BY 1") == [("223462", False), ("223465", False)]
    assert q(con, "SELECT stale_member FROM tgt_member_in") == [(True,)]


def test_redemptions_are_flattened_and_follow_the_member():
    con, _ = run(":memory:", FILES)
    assert q(con, "SELECT txn_id FROM fact_redemption ORDER BY 1") == [("RX10091",), ("RX10092",), ("RX10094",)]
    assert q(con, "SELECT reason FROM quarantine WHERE source = 'redemption_feed' ORDER BY 1") == [
        ("duplicate_txn_id",), ("invalid_status",), ("unknown_member",)]
    assert q(con, redemptions.REDEMPTION_BY_COUNTRY_SQL) == [
        ("CA", "AeroLink", 1, 12000, 0), ("CA", "SkyPoints", 1, 0, 5000), ("IN", "AeroLink", 1, 3000, 0)]


def test_running_everything_twice_changes_nothing():
    con, _ = run(":memory:", FILES)
    before = [q(con, f"SELECT count(*) FROM {t}")[0][0] for t in ("tgt_member_us", "tgt_member_ca", "fact_redemption", "quarantine")]
    process_redemption_file(con, SAMPLE / "SKYPOINTS_REDEMPTIONS_20240115.json")
    after = [q(con, f"SELECT count(*) FROM {t}")[0][0] for t in ("tgt_member_us", "tgt_member_ca", "fact_redemption", "quarantine")]
    assert before == after