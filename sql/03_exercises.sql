-- =============================================================
-- DekaBank Interview Prep: SQL EXERCISES (10 tasks)
-- Work through these BEFORE looking at 04_solutions.sql!
-- =============================================================
SET search_path TO deka;

-- ============================================================
-- WARM-UP (Exercises 1-3)
-- ============================================================

-- Exercise 1 [EASY]
-- List all active funds with their fund type and TER (Total Expense Ratio),
-- sorted by TER ascending.
-- Expected columns: fund_name, fund_type, ter

-- YOUR QUERY HERE:


-- Exercise 2 [EASY]
-- Count the number of customers per risk profile.
-- Sort by customer count descending.
-- Expected columns: risk_profile, customer_count

-- YOUR QUERY HERE:


-- Exercise 3 [EASY]
-- Show the total amount (amount_eur) and total transactions count
-- per transaction type (BUY, SELL, etc.) for the last 90 days.
-- Expected columns: transaction_type, txn_count, total_amount_eur

-- YOUR QUERY HERE:


-- ============================================================
-- INTERMEDIATE (Exercises 4-7)
-- ============================================================

-- Exercise 4 [MEDIUM]
-- Find the top 5 Sparkassen by net inflow (BUY minus SELL in EUR)
-- for the last 30 days. Include Sparkassen with zero activity.
-- Expected columns: sparkasse_name, total_buys, total_sells, net_inflow

-- YOUR QUERY HERE:


-- Exercise 5 [MEDIUM]
-- For each fund, calculate the month-over-month NAV price change (%)
-- for the last 6 months. Use window functions.
-- Expected columns: fund_name, nav_date, nav_price, prev_nav, mom_return_pct

-- YOUR QUERY HERE:


-- Exercise 6 [MEDIUM]
-- Classify each customer into AuM tiers based on their total portfolio value:
--   Premium  : >= 500,000 EUR
--   Standard : >= 50,000 EUR
--   Basic    : < 50,000 EUR
-- Show count and average AuM per tier.
-- Expected columns: tier, customer_count, avg_aum_eur

-- YOUR QUERY HERE:


-- Exercise 7 [MEDIUM]
-- For each depot, show the most recent transaction date and
-- the number of days since that transaction ("dormant days").
-- Flag depots inactive for > 180 days as 'DORMANT'.
-- Expected columns: depot_number, sparkasse_name, last_txn_date, dormant_days, status

-- YOUR QUERY HERE:


-- ============================================================
-- ADVANCED (Exercises 8-10)
-- ============================================================

-- Exercise 8 [HARD]
-- DATA QUALITY CHECK
-- Find all transactions where:
--   a) amount_eur is negative or zero
--   b) settlement_date is before transaction_date
--   c) settlement_date is more than 3 business days after transaction_date (T+3 breach)
--   d) nav_price is NULL for settled transactions
-- Return each issue type with count and sample transaction_ids.
-- Expected columns: issue_type, issue_count, sample_txn_ids

-- YOUR QUERY HERE:


-- Exercise 9 [HARD]
-- RUNNING CUMULATIVE NET INFLOW
-- Calculate the cumulative net inflow per fund over all time,
-- ordered by date. Show only the last 12 months.
-- Use window functions with ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW.
-- Expected columns: fund_name, txn_date, daily_net_flow, cumulative_net_flow

-- YOUR QUERY HERE:


-- Exercise 10 [HARD]
-- SPARKASSE PERFORMANCE RANKING
-- For each Sparkasse, calculate:
--   - Total AuM (current holdings * latest NAV)
--   - Total net inflow last 12 months
--   - Number of active depots
--   - AuM rank within their region (using RANK())
-- Expected columns: sparkasse_name, region, total_aum, net_inflow_12m,
--                   active_depots, region_aum_rank

-- YOUR QUERY HERE:
