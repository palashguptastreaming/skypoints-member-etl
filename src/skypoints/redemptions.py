"""Turns the partner JSON feed into one row per redemption transaction."""
import json
from datetime import datetime

from .config import REDEMPTION_STATUSES
from .db import insert_many
from .parse import Reject


def _date(value):
    try:
        return datetime.strptime(str(value), "%Y%m%d").date()
    except (TypeError, ValueError):
        return None


def flatten(doc):
    out = []
    for t in doc.get("redemptions") or []:
        out.append({"member_id": str(doc.get("member_id", "")).strip(), "feed_date": doc.get("feed_date"),
                    "txn_id": str(t.get("txn_id", "")).strip(), "txn_date": t.get("txn_date"),
                    "partner": t.get("partner"), "miles_redeemed": t.get("miles_redeemed"),
                    "status": str(t.get("status", "")).strip().upper()})
    return out


def load_redemptions(con, file_name, file_date, docs):
    con.execute("DELETE FROM raw_redemption_json WHERE file_name = ?", [file_name])
    insert_many(con, "INSERT INTO raw_redemption_json VALUES (?,?,?)",
                [(file_name, file_date, json.dumps(d)) for d in docs])
    con.execute("DELETE FROM quarantine WHERE source = 'redemption_feed' AND file_name = ?", [file_name])

    good, rejects, seen = [], [], {}
    for d in docs:
        if not str(d.get("member_id", "")).strip():
            rejects.append(Reject("?", "missing_member_id", json.dumps(d)[:200]))
            continue
        for r in flatten(d):
            feed_date = _date(r["feed_date"]) or file_date
            txn_date = _date(r["txn_date"])
            miles = r["miles_redeemed"]
            reason = None
            if not r["txn_id"]:
                reason = "missing_txn_id"
            elif txn_date is None:
                reason = "invalid_txn_date"
            elif r["status"] not in REDEMPTION_STATUSES:
                reason = "invalid_status"
            elif not isinstance(miles, int) or isinstance(miles, bool) or miles < 0:
                reason = "invalid_miles"
            elif r["txn_id"] in seen:
                reason = "duplicate_txn_id"
            if reason:
                rejects.append(Reject(r["txn_id"] or "?", reason, json.dumps(r)[:200]))
                continue
            seen[r["txn_id"]] = True
            good.append((r["txn_id"], r["member_id"], txn_date, r["partner"], miles, r["status"], feed_date, file_name))

    known = {m for (m,) in con.execute("SELECT member_id FROM member_country_index").fetchall()}
    final = []
    for row in good:
        if row[1] in known:
            final.append(row)
        else:
            rejects.append(Reject(row[0], "unknown_member", f"member_id={row[1]} has no profile record"))

    con.execute("BEGIN")
    try:
        insert_many(con, "DELETE FROM fact_redemption WHERE txn_id = ?", [(r[0],) for r in final])
        insert_many(con, "INSERT INTO fact_redemption VALUES (?,?,?,?,?,?,?,?)", final)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    insert_many(con, "INSERT INTO quarantine (source, file_name, row_ref, reason, detail) "
                     "VALUES ('redemption_feed', ?, ?, ?, ?)",
                [(file_name, r.row_ref, r.reason, r.detail) for r in rejects])
    return {"loaded": len(final), "quarantined": len(rejects)}


REDEMPTION_BY_COUNTRY_SQL = """
SELECT i.country_iso2, f.partner,
       count(*) AS transactions,
       sum(CASE WHEN f.status = 'COMPLETED' THEN f.miles_redeemed ELSE 0 END) AS miles_completed,
       sum(CASE WHEN f.status = 'PENDING'   THEN f.miles_redeemed ELSE 0 END) AS miles_pending
FROM fact_redemption f
JOIN member_country_index i ON i.member_id = f.member_id
GROUP BY 1, 2 ORDER BY 1, 2
"""