"""Raw -> staging for the member file, plus the checks that run on the way."""
from .config import DATE_FORMAT, DOB_FORMAT, FIELD_LENGTHS, NULL_TOKENS, STALE_DAYS
from .db import insert_many, read_sql


class ReconciliationError(Exception):
    """Raw and staging disagree: something was lost or changed during staging."""


def load_raw(con, file_name, file_date, rows):
    con.execute("DELETE FROM raw_member_file WHERE file_name = ?", [file_name])      # makes a re-run safe
    insert_many(
        con, "INSERT INTO raw_member_file VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(file_name, file_date, r["row_num"], r["member_name"], r["member_id"], r["enrollment_date"],
          r["last_flight_date"], r["tier_code"], r["agent_name"], r["state"], r["country"],
          r["post_code"], r["dob"], r["is_active"]) for r in rows])


def quarantine_rejects(con, source, file_name, rejects):
    insert_many(con, "INSERT INTO quarantine (source, file_name, row_ref, reason, detail) VALUES (?,?,?,?,?)",
                [(source, file_name, r.row_ref, r.reason, r.detail) for r in rejects])


def stage_members(con, file_name, run_date):
    """Build stg_member (clean rows with Age and Stale_Member) and move failing rows to quarantine."""
    sql = read_sql("03_staging_member.sql.tmpl").format(
        date_fmt=DATE_FORMAT, dob_fmt=DOB_FORMAT, stale_days=STALE_DAYS,
        null_tokens=",".join(repr(t) for t in NULL_TOKENS), len_name=FIELD_LENGTHS["member_name"],
        len_id=FIELD_LENGTHS["member_id"], len_tier=FIELD_LENGTHS["tier_code"], len_state=FIELD_LENGTHS["state"])
    first, second = [s for s in sql.split(";") if s.strip()]
    con.execute(first, [file_name])
    con.execute(second, [run_date, run_date, run_date])
    con.execute("DELETE FROM quarantine WHERE source = 'member_file' AND file_name = ? AND reason NOT IN "
                "('unknown_record_type','column_count_mismatch')", [file_name])
    con.execute("""
        INSERT INTO quarantine (source, file_name, row_ref, reason, detail)
        SELECT 'member_file', file_name, CAST(row_num AS VARCHAR), final_reason,
               'member_id=' || coalesce(member_id, '') || '; name=' || coalesce(member_name, '')
        FROM stg_member_all WHERE final_reason IS NOT NULL""")


def reconcile(con, file_name):
    """Every raw data row is either staged or quarantined, and no column lost values on the way."""
    raw_rows = con.execute("SELECT count(*) FROM raw_member_file WHERE file_name=? AND row_num>1",
                           [file_name]).fetchone()[0]
    staged = con.execute("SELECT count(*) FROM stg_member").fetchone()[0]
    rejected = con.execute("SELECT count(*) FROM stg_member_all WHERE final_reason IS NOT NULL").fetchone()[0]
    if raw_rows != staged + rejected:
        raise ReconciliationError(f"{raw_rows} raw rows but {staged} staged + {rejected} quarantined")
    tokens = ",".join(repr(t) for t in NULL_TOKENS)
    for raw_col, stg_col in [("member_name", "member_name"), ("tier_code", "tier_code"),
                             ("agent_name", "agent_name"), ("state", "state")]:
        # values that are really "no value" (blank, NULL, N/A) are not expected to survive staging
        raw_n = con.execute(f"""
            SELECT count(*) FROM raw_member_file r
            WHERE r.file_name = ? AND r.row_num > 1 AND trim(coalesce(r.{raw_col}, '')) <> ''
              AND upper(trim(r.{raw_col})) NOT IN ({tokens})
              AND r.row_num IN (SELECT row_num FROM stg_member)""", [file_name]).fetchone()[0]
        stg_n = con.execute(f"SELECT count(*) FROM stg_member WHERE {stg_col} IS NOT NULL").fetchone()[0]
        if raw_n != stg_n:
            raise ReconciliationError(f"Column {raw_col}: {raw_n} non-empty values in raw, {stg_n} in staging")