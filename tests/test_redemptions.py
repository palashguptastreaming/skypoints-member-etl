"""Tests for the redemption feed: flattening, validation, quarantine and the join to members."""
from datetime import date

from skypoints import country_split, redemptions, staging
from skypoints.parse import file_date_from_name, parse_member_file

FEED_DATE = date(2024, 1, 15)


def add_members(con, make_members, *lines):
    path = make_members("20240115", *lines)
    rows, _, _ = parse_member_file(path)
    staging.load_raw(con, path.name, file_date_from_name(path), rows)
    staging.stage_members(con, path.name, file_date_from_name(path))
    country_split.apply_country_split(con)


def txn(txn_id, status="COMPLETED", miles=1000, partner="AeroLink", txn_date="20240110"):
    return {"txn_id": txn_id, "txn_date": txn_date, "partner": partner, "miles_redeemed": miles, "status": status}


def doc(member_id, *txns):
    return {"member_id": member_id, "feed_date": "20240115", "redemptions": list(txns)}


def load(con, *docs):
    return redemptions.load_redemptions(con, "SKYPOINTS_REDEMPTIONS_20240115.json", FEED_DATE, list(docs))


def q(con, sql):
    return con.execute(sql).fetchall()


def test_one_row_per_transaction(con, make_members):
    add_members(con, make_members, "D|A|1|20200101||||NY|USA||")
    result = load(con, doc("1", txn("T1"), txn("T2", "PENDING", 5000)))
    assert result == {"loaded": 2, "quarantined": 0}
    assert q(con, "SELECT txn_id, status, miles_redeemed FROM fact_redemption ORDER BY 1") == [
        ("T1", "COMPLETED", 1000), ("T2", "PENDING", 5000)]


def test_bad_transactions_are_quarantined_with_reason(con, make_members):
    add_members(con, make_members, "D|A|1|20200101||||NY|USA||")
    load(con, doc("1", txn("T1"), txn("T1"), txn("T2", "WEIRD"), txn("T3", txn_date="2024-13-45"),
                  txn("T4", miles=-5), txn("T5", miles="lots")),
         doc("999", txn("T6")))
    assert [r[0] for r in q(con, "SELECT txn_id FROM fact_redemption")] == ["T1"]
    assert sorted(r[0] for r in q(con, "SELECT reason FROM quarantine")) == [
        "duplicate_txn_id", "invalid_miles", "invalid_miles", "invalid_status", "invalid_txn_date", "unknown_member"]


def test_status_is_case_insensitive(con, make_members):
    add_members(con, make_members, "D|A|1|20200101||||NY|USA||")
    load(con, doc("1", txn("T1", "completed")))
    assert q(con, "SELECT status FROM fact_redemption") == [("COMPLETED",)]


def test_reloading_the_same_feed_is_idempotent(con, make_members):
    add_members(con, make_members, "D|A|1|20200101||||NY|USA||")
    for _ in range(2):
        load(con, doc("1", txn("T1"), txn("T2")), doc("999", txn("T3")))
    assert q(con, "SELECT count(*) FROM fact_redemption") == [(2,)]
    assert q(con, "SELECT count(*) FROM quarantine") == [(1,)]
    assert q(con, "SELECT count(*) FROM raw_redemption_json") == [(2,)]


def test_a_corrected_transaction_replaces_the_old_one(con, make_members):
    add_members(con, make_members, "D|A|1|20200101||||NY|USA||")
    load(con, doc("1", txn("T1", "PENDING")))
    load(con, doc("1", txn("T1", "COMPLETED")))
    assert q(con, "SELECT status FROM fact_redemption") == [("COMPLETED",)]


def test_document_without_member_id_is_quarantined(con, make_members):
    add_members(con, make_members, "D|A|1|20200101||||NY|USA||")
    load(con, {"feed_date": "20240115", "redemptions": [txn("T1")]})
    assert q(con, "SELECT reason FROM quarantine") == [("missing_member_id",)]


def test_join_follows_the_member_to_their_new_country(con, make_members):
    add_members(con, make_members, "D|A|1|20200101||||NY|USA||", "D|B|2|20200101||||KA|IND||")
    load(con, doc("1", txn("T1", miles=5000), txn("T2", "PENDING", 2000)), doc("2", txn("T3", miles=1500)))
    assert q(con, redemptions.REDEMPTION_BY_COUNTRY_SQL) == [
        ("IN", "AeroLink", 1, 1500, 0), ("US", "AeroLink", 2, 5000, 2000)]
    moved = make_members("20240116", "D|A|1|20200101||||ON|CAN||")
    rows, _, _ = parse_member_file(moved)
    staging.load_raw(con, moved.name, file_date_from_name(moved), rows)
    staging.stage_members(con, moved.name, file_date_from_name(moved))
    country_split.apply_country_split(con)
    assert q(con, redemptions.REDEMPTION_BY_COUNTRY_SQL) == [
        ("CA", "AeroLink", 2, 5000, 2000), ("IN", "AeroLink", 1, 1500, 0)]