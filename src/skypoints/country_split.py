"""Writes each clean member into the table of their current country.

A member lives in exactly one country table. When a member appears with a new country, the old
row is removed and the new one is written, all in one transaction. An index table remembers each
member's newest file date, so loading an older file again cannot move a member back.
"""
from .db import ensure_target, target_tables

TARGET_COLUMNS = ("member_id, member_name, enrollment_date, last_flight_date, tier_code, agent_name, state, "
                  "country_iso2, post_code, dob, is_active, age, stale_member")


def apply_country_split(con):
    con.execute("BEGIN")
    try:
        con.execute("""
            CREATE OR REPLACE TEMP TABLE batch_eff AS
            SELECT s.* FROM stg_member s
            LEFT JOIN member_country_index i ON i.member_id = s.member_id
            WHERE i.member_id IS NULL OR i.file_date <= s.file_date""")
        for table in target_tables(con):
            con.execute(f"DELETE FROM {table} WHERE member_id IN (SELECT member_id FROM batch_eff)")
        written = {}
        for (cc,) in con.execute("SELECT DISTINCT country_iso2 FROM batch_eff ORDER BY 1").fetchall():
            table = ensure_target(con, cc)
            con.execute(f"""INSERT INTO {table} ({TARGET_COLUMNS}, source_file, file_date)
                            SELECT {TARGET_COLUMNS}, file_name, file_date FROM batch_eff WHERE country_iso2 = ?""", [cc])
            written[cc] = con.execute("SELECT count(*) FROM batch_eff WHERE country_iso2 = ?", [cc]).fetchone()[0]
        con.execute("DELETE FROM member_country_index WHERE member_id IN (SELECT member_id FROM batch_eff)")
        con.execute("INSERT INTO member_country_index SELECT member_id, country_iso2, file_date FROM batch_eff")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return written