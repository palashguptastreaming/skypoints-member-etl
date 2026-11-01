"""Tests for the country split: one table per country, latest record wins, safe to rerun."""
from skypoints import country_split, staging
from skypoints.parse import file_date_from_name, parse_member_file


def load(con, path):
    rows, rejects, _ = parse_member_file(path)
    run_date = file_date_from_name(path)
    staging.load_raw(con, path.name, run_date, rows)
    staging.stage_members(con, path.name, run_date)
    return country_split.apply_country_split(con)


def q(con, sql):
    return con.execute(sql).fetchall()


def test_each_country_gets_its_own_table(con, make_members):
    p = make_members("20240115", *[f"D|N{i}|{i}|20200101|||||{c}||" for i, c in
                                   enumerate(["USA", "ind", "PHIL", "Canada", "AU"], 1)])
    written = load(con, p)
    assert written == {"AU": 1, "CA": 1, "IN": 1, "PH": 1, "US": 1}
    assert {t for t in map(lambda r: r[0], q(con, "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'tgt_%'"))} == {
        "tgt_member_au", "tgt_member_ca", "tgt_member_in", "tgt_member_ph", "tgt_member_us"}


def test_member_moving_country_is_in_one_table_only(con, make_members):
    load(con, make_members("20240115", "D|E|1|20200101||||NY|USA||"))
    load(con, make_members("20240116", "D|E|1|20200101||||ON|CAN||"))
    assert q(con, "SELECT count(*) FROM tgt_member_us") == [(0,)]
    assert q(con, "SELECT count(*) FROM tgt_member_ca") == [(1,)]
    assert q(con, "SELECT country_iso2, file_date::VARCHAR FROM member_country_index") == [("CA", "2024-01-16")]


def test_replaying_an_old_file_does_not_undo_a_move(con, make_members):
    old = make_members("20240115", "D|E|1|20200101||||NY|USA||")
    new = make_members("20240116", "D|E|1|20200101||||ON|CAN||")
    load(con, old); load(con, new); load(con, old)
    assert q(con, "SELECT count(*) FROM tgt_member_us") == [(0,)]
    assert q(con, "SELECT country_iso2 FROM member_country_index") == [("CA",)]


def test_rerunning_the_same_file_is_idempotent(con, make_members):
    p = make_members("20240115", "D|E|1|20200101||||NY|USA||", "D|F|2|20200101||||NY|USA||")
    load(con, p); load(con, p)
    assert q(con, "SELECT count(*) FROM tgt_member_us") == [(2,)]
    assert q(con, "SELECT count(*) FROM raw_member_file") == [(2,)]


def test_other_members_are_untouched_when_one_moves(con, make_members):
    load(con, make_members("20240115", "D|E|1|20200101||||NY|USA||", "D|F|2|20200101||||NY|USA||"))
    load(con, make_members("20240116", "D|E|1|20200101||||ON|CAN||"))
    assert q(con, "SELECT member_id FROM tgt_member_us") == [("2",)]
    assert q(con, "SELECT member_id FROM tgt_member_ca") == [("1",)]


def test_changed_details_replace_the_old_row(con, make_members):
    load(con, make_members("20240115", "D|Old Name|1|20200101||||NY|USA||"))
    load(con, make_members("20240116", "D|New Name|1|20200101||||NY|USA||"))
    assert q(con, "SELECT member_name, file_date::VARCHAR FROM tgt_member_us") == [("New Name", "2024-01-16")]