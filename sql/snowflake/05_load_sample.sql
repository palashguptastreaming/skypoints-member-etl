-- Snowflake: loads the sample member files and redemption feed into the raw tables, the same rows the Python parser produces.
-- Run after 01_tables.sql. Rows rejected before raw in Python (wrong column count, unknown record type) are not in this script.

DELETE FROM RAW_MEMBER_FILE WHERE FILE_NAME = 'SKYPOINTS_MEMBERS_20240115.txt';
INSERT INTO RAW_MEMBER_FILE (FILE_NAME, FILE_DATE, ROW_NUM, MEMBER_NAME, MEMBER_ID, ENROLLMENT_DATE, LAST_FLIGHT_DATE, TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB, IS_ACTIVE) VALUES
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 2, 'Elena', '223457', '20101012', '20121013', 'GLD', 'Sam', 'CA', 'USA', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 3, 'Ravi', '223458', '20101012', '20121013', 'SLV', 'Sam', 'TN', 'IND', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 4, 'Mateo', '223459', '20101012', '20121013', 'GLD', 'Sam', 'NCR', 'PHIL', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 5, 'Nora', '22345', '20101012', '20121013', 'PLT', 'Sam', 'ONT', 'CAN', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 6, 'Jacob', '2256', '20101012', '20121013', 'SLV', 'Sam', 'VIC', 'AU', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 7, '', '223460', '20101012', '20240101', 'GLD', 'Sam', 'CA', 'USA', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 8, 'No Id', '', '20101012', '20240101', 'GLD', 'Sam', 'CA', 'USA', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 9, 'Bad Date', '223461', '2010-10-12', '20240101', 'GLD', 'Sam', 'CA', 'USA', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 10, 'Dup One', '223462', '20101012', '20240101', 'GLD', 'Sam', 'CA', 'USA', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 11, 'Dup Two', '223462', '20101012', '20240102', 'GLD', 'Sam', 'CA', 'USA', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 13, 'Mars', '223464', '20101012', '20240101', 'GLD', 'Sam', 'XX', 'MARS', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240115.txt', '2024-01-15', 14, 'Recent', '223465', '20101012', '20240101', 'GLD', 'Sam', 'CA', 'USA', NULL, '03051985', 'A');

DELETE FROM RAW_MEMBER_FILE WHERE FILE_NAME = 'SKYPOINTS_MEMBERS_20240116.txt';
INSERT INTO RAW_MEMBER_FILE (FILE_NAME, FILE_DATE, ROW_NUM, MEMBER_NAME, MEMBER_ID, ENROLLMENT_DATE, LAST_FLIGHT_DATE, TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB, IS_ACTIVE) VALUES
    ('SKYPOINTS_MEMBERS_20240116.txt', '2024-01-16', 2, 'Elena', '223457', '20101012', '20240110', 'GLD', 'Sam', 'ON', 'CAN', NULL, '03051985', 'A'),
    ('SKYPOINTS_MEMBERS_20240116.txt', '2024-01-16', 3, 'Leo', '223466', '20101012', '20231201', 'SLV', 'Sam', 'NSW', 'AU', NULL, '3051985', 'A');

DELETE FROM RAW_REDEMPTION_JSON WHERE FILE_NAME = 'SKYPOINTS_REDEMPTIONS_20240115.json';
INSERT INTO RAW_REDEMPTION_JSON (FILE_NAME, FEED_DATE, PAYLOAD) SELECT 'SKYPOINTS_REDEMPTIONS_20240115.json', '2024-01-15', PARSE_JSON('{"member_id": "223457", "feed_date": "20240115", "redemptions": [{"txn_id": "RX10091", "txn_date": "20240110", "partner": "AeroLink", "miles_redeemed": 12000, "status": "COMPLETED"}, {"txn_id": "RX10092", "txn_date": "20240113", "partner": "SkyPoints", "miles_redeemed": 5000, "status": "PENDING"}, {"txn_id": "RX10091", "txn_date": "20240110", "partner": "AeroLink", "miles_redeemed": 12000, "status": "COMPLETED"}]}');
INSERT INTO RAW_REDEMPTION_JSON (FILE_NAME, FEED_DATE, PAYLOAD) SELECT 'SKYPOINTS_REDEMPTIONS_20240115.json', '2024-01-15', PARSE_JSON('{"member_id": "223458", "feed_date": "20240115", "redemptions": [{"txn_id": "RX10093", "txn_date": "20240111", "partner": "AeroLink", "miles_redeemed": 800, "status": "WEIRD"}, {"txn_id": "RX10094", "txn_date": "20240112", "partner": "AeroLink", "miles_redeemed": 3000, "status": "COMPLETED"}]}');
INSERT INTO RAW_REDEMPTION_JSON (FILE_NAME, FEED_DATE, PAYLOAD) SELECT 'SKYPOINTS_REDEMPTIONS_20240115.json', '2024-01-15', PARSE_JSON('{"member_id": "999999", "feed_date": "20240115", "redemptions": [{"txn_id": "RX10095", "txn_date": "20240114", "partner": "AeroLink", "miles_redeemed": 100, "status": "COMPLETED"}]}');