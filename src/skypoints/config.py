"""All business rules live here so they are written once and can be tested."""

REQUIRED_COLUMNS = ["Member_Name", "Member_Id", "Enrollment_Date"]
OPTIONAL_COLUMNS = ["Last_Flight_Date", "Tier_Code", "Agent_Name", "State",
                    "Country", "Post_Code", "DOB", "Is_Active"]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

DATE_FORMAT = "%Y%m%d"      # Enrollment_Date, Last_Flight_Date, txn_date, feed_date
DOB_FORMAT = "%d%m%Y"       # ASSUMPTION: DOB arrives as DDMMYYYY (03051985 = 3 May 1985). Confirm with the client.
STALE_DAYS = 90             # Stale_Member = more than 90 days since last flight

TIER_CODES = {"GLD", "SLV", "PLT"}
ACTIVE_FLAGS = {"A", "I"}
REDEMPTION_STATUSES = {"COMPLETED", "PENDING", "CANCELLED"}

# Raw country value (upper case) -> ISO 3166 alpha-2. Anything not listed is quarantined.
COUNTRY_MAP = {
    "US": "US", "USA": "US", "UNITED STATES": "US",
    "IN": "IN", "IND": "IN", "INDIA": "IN",
    "CA": "CA", "CAN": "CA", "CANADA": "CA",
    "PH": "PH", "PHL": "PH", "PHIL": "PH", "PHILIPPINES": "PH",
    "AU": "AU", "AUS": "AU", "AUSTRALIA": "AU",
    "GB": "GB", "UK": "GB", "GBR": "GB",
    "SG": "SG", "SGP": "SG", "AE": "AE", "ARE": "AE", "UAE": "AE",
}

# Data-quality thresholds for warnings (warnings never stop a load; quarantine rules do).
DOMINANT_VALUE_SHARE = 0.5   # warn when one value fills at least this share of a column
DOMINANT_MIN_ROWS = 3

# Max lengths from the design document's detail-record table.
FIELD_LENGTHS = {"member_name": 255, "member_id": 18, "tier_code": 5, "agent_name": 255, "state": 5,
                 "country": 5, "post_code": 5, "is_active": 1}
NULL_TOKENS = ("NULL", "NONE", "N/A", "NA", "NAN")   # text that really means "no value"
