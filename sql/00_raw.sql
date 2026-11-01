-- Layer 1: RAW. Everything arrives as text, exactly as received, plus lineage columns.
-- Written in the SQL shared by Snowflake and DuckDB so the same file runs in both.
CREATE TABLE IF NOT EXISTS raw_member_file (
    file_name        VARCHAR NOT NULL,
    file_date        DATE    NOT NULL,
    row_num          INTEGER NOT NULL,      -- line number in the file (header = 1)
    member_name      VARCHAR,
    member_id        VARCHAR,
    enrollment_date  VARCHAR,
    last_flight_date VARCHAR,
    tier_code        VARCHAR,
    agent_name       VARCHAR,
    state            VARCHAR,
    country          VARCHAR,
    post_code        VARCHAR,
    dob              VARCHAR,
    is_active        VARCHAR
);

-- The whole partner document is kept untouched. In Snowflake the payload column would be VARIANT.
CREATE TABLE IF NOT EXISTS raw_redemption_json (
    file_name VARCHAR NOT NULL,
    feed_date DATE    NOT NULL,
    payload   VARCHAR NOT NULL
);