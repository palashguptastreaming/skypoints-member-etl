-- Reference, control and output tables that are not country specific.
CREATE TABLE IF NOT EXISTS country_map (
    raw_value    VARCHAR PRIMARY KEY,       -- upper-case value as found in the feed
    country_iso2 VARCHAR NOT NULL
);

-- Rows that failed a check, with the reason. Nothing is silently dropped.
CREATE TABLE IF NOT EXISTS quarantine (
    source     VARCHAR NOT NULL,            -- member_file | redemption_feed
    file_name  VARCHAR NOT NULL,
    row_ref    VARCHAR,                     -- row number or txn id
    reason     VARCHAR NOT NULL,
    detail     VARCHAR,
    loaded_at  TIMESTAMP DEFAULT current_timestamp
);

-- Non-fatal findings (suspicious but loadable data) per run.
CREATE TABLE IF NOT EXISTS dq_warning (
    file_name VARCHAR NOT NULL,
    code      VARCHAR NOT NULL,
    row_count INTEGER NOT NULL,
    message   VARCHAR NOT NULL
);

-- One row per member: which country table currently holds them, and from which file.
-- This is what makes "latest record wins" safe, including when an old file is replayed.
CREATE TABLE IF NOT EXISTS member_country_index (
    member_id    VARCHAR PRIMARY KEY,
    country_iso2 VARCHAR NOT NULL,
    file_date    DATE    NOT NULL
);

-- Flattened redemptions: one row per transaction.
CREATE TABLE IF NOT EXISTS fact_redemption (
    txn_id         VARCHAR PRIMARY KEY,
    member_id      VARCHAR NOT NULL,
    txn_date       DATE    NOT NULL,
    partner        VARCHAR,
    miles_redeemed INTEGER NOT NULL,
    status         VARCHAR NOT NULL,
    feed_date      DATE    NOT NULL,
    source_file    VARCHAR NOT NULL
);
-- Snowflake: ALTER TABLE fact_redemption CLUSTER BY (member_id);