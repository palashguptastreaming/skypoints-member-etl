"""Data-quality warnings: suspicious data that is still loaded (quarantine handles the rows that are rejected)."""
from collections import Counter

from .config import ACTIVE_FLAGS, DOMINANT_MIN_ROWS, DOMINANT_VALUE_SHARE, TIER_CODES
from .db import insert_many


def collect_warnings(con, file_name, header_columns):
    """Suspicious but loadable data. Returns (code, count, message) tuples."""
    out = []
    missing = [c for c in ("Post_Code",) if c.lower() not in {h.lower() for h in header_columns}]
    if missing:
        out.append(("missing_optional_column", len(missing), f"Header has no {missing} although the spec lists it"))

    dobs = [r[0] for r in con.execute("SELECT dob FROM stg_member WHERE dob IS NOT NULL").fetchall()]
    if len(dobs) >= DOMINANT_MIN_ROWS:
        value, n = Counter(dobs).most_common(1)[0]
        if n / len(dobs) >= DOMINANT_VALUE_SHARE:
            out.append(("dominant_dob", n, f"{n} of {len(dobs)} members share DOB {value}; likely a placeholder, Age is unreliable"))

    n = con.execute("""SELECT count(*) FROM raw_member_file r WHERE r.file_name=? AND r.row_num>1
                       AND trim(coalesce(r.dob,''))<>'' AND r.row_num IN
                       (SELECT row_num FROM stg_member WHERE dob IS NULL)""", [file_name]).fetchone()[0]
    if n:
        out.append(("unparseable_dob", n, "DOB present but not in the expected DDMMYYYY format"))

    n = con.execute("""SELECT count(*) FROM raw_member_file r WHERE r.file_name=? AND r.row_num>1
                       AND trim(coalesce(r.last_flight_date,''))<>'' AND r.row_num IN
                       (SELECT row_num FROM stg_member WHERE last_flight_date IS NULL)""", [file_name]).fetchone()[0]
    if n:
        out.append(("unparseable_last_flight_date", n, "Last_Flight_Date present but not YYYYMMDD"))

    n = con.execute("""SELECT count(*) FROM raw_member_file r WHERE r.file_name=? AND r.row_num>1
                       AND regexp_matches(trim(r.dob), '^[0-9]{7}$')""", [file_name]).fetchone()[0]
    if n:
        out.append(("dob_leading_zero_repaired", n, "7-digit DOB left-padded to 8 (numeric type stripped the leading zero upstream)"))

    n = con.execute("SELECT count(*) FROM (SELECT member_name FROM stg_member GROUP BY 1 HAVING count(DISTINCT member_id) > 1)").fetchone()[0]
    if n:
        out.append(("same_name_different_member_id", n, "Spec marks Member_Name as the key column, but the same name appears under different ids"))

    lengths = Counter(len(r[0]) for r in con.execute("SELECT member_id FROM stg_member").fetchall())
    if len(lengths) > 1:
        common = lengths.most_common(1)[0][0]
        odd = sum(c for length, c in lengths.items() if length != common)
        out.append(("member_id_length_outlier", odd, f"{odd} member ids differ in length from the usual {common} characters"))

    n = con.execute(f"SELECT count(*) FROM stg_member WHERE tier_code IS NOT NULL AND tier_code NOT IN "
                    f"({','.join(repr(t) for t in sorted(TIER_CODES))})").fetchone()[0]
    if n:
        out.append(("unknown_tier_code", n, "Tier code outside GLD/SLV/PLT"))
    n = con.execute(f"SELECT count(*) FROM stg_member WHERE is_active IS NOT NULL AND is_active NOT IN "
                    f"({','.join(repr(t) for t in sorted(ACTIVE_FLAGS))})").fetchone()[0]
    if n:
        out.append(("unknown_active_flag", n, "Is_Active outside A/I"))
    return out


def store_warnings(con, file_name, warnings):
    con.execute("DELETE FROM dq_warning WHERE file_name = ?", [file_name])
    insert_many(con, "INSERT INTO dq_warning VALUES (?,?,?,?)", [(file_name, c, n, m) for c, n, m in warnings])