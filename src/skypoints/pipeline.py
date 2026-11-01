"""Runs the whole pipeline from the command line.

Usage: python -m skypoints.pipeline --db skypoints.duckdb data/sample/*

Files are processed in date order, member files before redemption files for the same day, because
redemptions are checked against known members. The date in the file name is used as "today" for Age
and Stale_Member, so the same file always gives the same result.
"""
import argparse
from pathlib import Path

from . import checks, country_split, redemptions, staging
from .db import connect, target_tables
from .parse import file_date_from_name, parse_member_file, parse_redemption_file


def process_member_file(con, path):
    path = Path(path)
    file_date = file_date_from_name(path)
    rows, rejects, header = parse_member_file(path)
    staging.load_raw(con, path.name, file_date, rows)
    con.execute("DELETE FROM quarantine WHERE source = 'member_file' AND file_name = ?", [path.name])
    staging.quarantine_rejects(con, "member_file", path.name, rejects)
    staging.stage_members(con, path.name, file_date)
    staging.reconcile(con, path.name)
    warnings = checks.collect_warnings(con, path.name, header)
    checks.store_warnings(con, path.name, warnings)
    written = country_split.apply_country_split(con)
    return {"file": path.name, "lines": len(rows) + len(rejects), "written_by_country": written,
            "warnings": [w[0] for w in warnings]}


def process_redemption_file(con, path):
    path = Path(path)
    summary = redemptions.load_redemptions(con, path.name, file_date_from_name(path), parse_redemption_file(path))
    return {"file": path.name, **summary}


def run(db_path, files):
    con = connect(db_path)
    ordered = sorted(files, key=lambda f: (file_date_from_name(f), "REDEMPTIONS" in Path(f).name.upper()))
    results = []
    for f in ordered:
        if "REDEMPTIONS" in Path(f).name.upper():
            results.append(process_redemption_file(con, f))
        else:
            results.append(process_member_file(con, f))
    return con, results


def print_report(con, results):
    for r in results:
        print(r)
    print("\nMembers per country table:")
    for table in sorted(target_tables(con)):
        print(f"  {table}: {con.execute(f'SELECT count(*) FROM {table}').fetchone()[0]}")
    print("\nQuarantine by reason:")
    for row in con.execute("SELECT source, reason, count(*) FROM quarantine GROUP BY 1, 2 ORDER BY 1, 2").fetchall():
        print(" ", row)
    print("\nWarnings:")
    for row in con.execute("SELECT file_name, code, row_count FROM dq_warning ORDER BY 1, 2").fetchall():
        print(" ", row)
    print("\nRedemptions by country and partner (country, partner, transactions, completed miles, pending miles):")
    for row in con.execute(redemptions.REDEMPTION_BY_COUNTRY_SQL).fetchall():
        print(" ", row)


def main():
    parser = argparse.ArgumentParser(description="Load SkyPoints member and redemption files.")
    parser.add_argument("--db", default="skypoints.duckdb", help="DuckDB file to write (default skypoints.duckdb)")
    parser.add_argument("files", nargs="+", help="member .txt and redemption .json files")
    args = parser.parse_args()
    con, results = run(args.db, args.files)
    print_report(con, results)


if __name__ == "__main__":
    main()