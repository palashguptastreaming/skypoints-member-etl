from pathlib import Path

import pytest

from skypoints.db import connect

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"
HEADER = "H|Member_Name|Member_Id|Enrollment_Date|Last_Flight_Date|Tier_Code|Agent_Name|State|Country|DOB|Is_Active\n"


@pytest.fixture
def con():
    """A fresh in-memory database with all raw and support tables."""
    return connect(":memory:")


@pytest.fixture
def make_members(tmp_path):
    """Write a small member file for a test and return its path."""
    def _make(date, *lines, header=HEADER):
        p = tmp_path / f"SKYPOINTS_MEMBERS_{date}.txt"
        p.write_text(header + "\n".join(lines) + "\n")
        return p
    return _make