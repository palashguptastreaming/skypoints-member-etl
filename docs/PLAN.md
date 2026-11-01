##My Understanding and Plan

##The task:
SkyPoints sends two daily feeds: a member file and a JSON file of mile redemptions. My job is to:
- put each member in their own country's table,
- add AGE (from date of birth) and Stale_member(no flight in more than 90 days),
- keep only the Latest_record if a member moved country,
- flatten the JSON into a normal table and explain how to join it to members,
- validate the data, and design it for billions of records a day.

##Problems I saw in the samples:
- Countries are written differently (USA, IND, PHIL, CAN, AU).
- Date of birth loses its leading zero (`03051985` becomes `3051985`), it could be day-month or month-day, and everyone has the same date.
- Agent name goes missing between the file and staging.
- Post code is in the spec but not in the file.
- Member ids have different lengths, and the spec calls Member Name (not Member ID) the key.
- The IND, USA and AUS samples use different column names and date formats:
  - IND: dates are M/D/YYYY (for example `8/13/1982`), and there is an extra Individual flag (I or C).
  - USA: dates are stored as numbers that lost their leading zero (`1052022` is `01052022`, MMDDYYYY), and there is no date of birth.
  - AUS: dates are ISO (`2022-05-11`), one date of birth is the text `NULL`, and one enrollment date is impossible (`2021-13-13`).
- Because the US and IND samples put the month first, the date of birth `03051985` may be MMDDYYYY and not DDMMYYYY.
- The JSON can have repeated transactions, odd statuses and members that do not exist.

##My plan
1. Raw: an exact copy of what arrived, all as text, so the original is always available.
2. Staging: clean the data, fix dates, standardise the country, and add Age and Stale_Member.
3. Country tables: one clean table per country.
4. Quarantiene: bad rows are kept in their own table with the reason, so nothing is lost and nothing bad gets in.
5. Latest record wins: a small index table remembers each member's newest country, so a reload or an old file cannot undo a move.
6. Safe to rerun: loading the same file twice gives the same result.
7. Checks: required fields, duplicate ids, real dates, lengths, known countries, and for the JSON: duplicate transactions, valid status, member exists.
8. Fixing problem on the way: restore leading zeros on dates, treat the text `NULL` as empty, and send impossible dates to quarantine.

##question to clients
1. Is the date of birth day-month-year or month-day-year? (The US and IND samples are month-first.)
2. Is the key the member name (as the spec says) or the member id?
3. Can Age stay empty for USA members, who have no date of birth?
4. Is the extra `Individual` flag in IND needed in the target table?