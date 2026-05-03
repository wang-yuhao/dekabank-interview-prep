-- =============================================================
-- DekaBank Interview Prep: SQL SOLUTIONS
-- Only read AFTER attempting 03_exercises.sql yourself!
-- =============================================================
SET search_path TO deka;

-- ============================================================
-- Solution 1: Active funds sorted by TER
-- ============================================================
SELECT fund_name, fund_type, ter
FROM funds
WHERE active = TRUE
ORDER BY ter ASC;


-- ============================================================
-- Solution 2: Customers per risk profile
-- ============================================================
SELECT
    risk_profile,
    COUNT(*) AS customer_count
FROM customers
GROUP BY risk_profile
ORDER BY customer_count DESC;


-- ============================================================
-- Solution 3: Transaction volume per type last 90 days
-- ============================================================
SELECT
    transaction_type,
    COUNT(*)              AS txn_count,
    ROUND(SUM(amount_eur), 2) AS total_amount_eur
FROM transactions
WHERE transaction_date >= CURRENT_DATE - INTERVAL '90 days'
  AND status = 'SETTLED'
GROUP BY transaction_type
ORDER BY total_amount_eur DESC;


-- ============================================================
-- Solution 4: Top 5 Sparkassen by net inflow last 30 days
-- ============================================================
WITH inflows AS (
    SELECT
        d.sparkasse_id,
        SUM(CASE WHEN t.transaction_type = 'BUY'  THEN t.amount_eur ELSE 0 END) AS total_buys,
        SUM(CASE WHEN t.transaction_type = 'SELL' THEN t.amount_eur ELSE 0 END) AS total_sells
    FROM transactions t
    JOIN depots d ON t.depot_id = d.depot_id
    WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '30 days'
      AND t.status = 'SETTLED'
    GROUP BY d.sparkasse_id
)
SELECT
    s.sparkasse_name,
    COALESCE(i.total_buys,  0) AS total_buys,
    COALESCE(i.total_sells, 0) AS total_sells,
    COALESCE(i.total_buys, 0) - COALESCE(i.total_sells, 0) AS net_inflow
FROM sparkassen s
LEFT JOIN inflows i ON s.sparkasse_id = i.sparkasse_id
ORDER BY net_inflow DESC
LIMIT 5;


-- ============================================================
-- Solution 5: Month-over-month NAV change (window function)
-- ============================================================
WITH monthly_nav AS (
    SELECT
        f.fund_name,
        DATE_TRUNC('month', fn.nav_date)::DATE AS nav_date,
        AVG(fn.nav_price)                       AS nav_price
    FROM fund_nav fn
    JOIN funds f ON fn.fund_id = f.fund_id
    WHERE fn.nav_date >= CURRENT_DATE - INTERVAL '6 months'
    GROUP BY f.fund_name, DATE_TRUNC('month', fn.nav_date)
)
SELECT
    fund_name,
    nav_date,
    ROUND(nav_price, 4) AS nav_price,
    ROUND(LAG(nav_price) OVER (PARTITION BY fund_name ORDER BY nav_date), 4) AS prev_nav,
    ROUND(
        (nav_price - LAG(nav_price) OVER (PARTITION BY fund_name ORDER BY nav_date))
        / NULLIF(LAG(nav_price) OVER (PARTITION BY fund_name ORDER BY nav_date), 0) * 100
    , 2) AS mom_return_pct
FROM monthly_nav
ORDER BY fund_name, nav_date;


-- ============================================================
-- Solution 6: Customer AuM tier classification
-- ============================================================
WITH customer_aum AS (
    SELECT
        c.customer_id,
        SUM(h.units * fn.nav_price) AS total_aum
    FROM customers c
    JOIN depots d    ON c.customer_id = d.customer_id
    JOIN holdings h  ON d.depot_id = h.depot_id
    JOIN fund_nav fn ON h.fund_id = fn.fund_id
                    AND fn.nav_date = (SELECT MAX(nav_date) FROM fund_nav WHERE fund_id = h.fund_id)
    GROUP BY c.customer_id
),
tiered AS (
    SELECT
        CASE
            WHEN total_aum >= 500000 THEN 'Premium'
            WHEN total_aum >= 50000  THEN 'Standard'
            ELSE 'Basic'
        END AS tier,
        total_aum
    FROM customer_aum
)
SELECT
    tier,
    COUNT(*)              AS customer_count,
    ROUND(AVG(total_aum), 2) AS avg_aum_eur
FROM tiered
GROUP BY tier
ORDER BY avg_aum_eur DESC;


-- ============================================================
-- Solution 7: Dormant depot detection
-- ============================================================
SELECT
    d.depot_number,
    s.sparkasse_name,
    MAX(t.transaction_date)                          AS last_txn_date,
    (CURRENT_DATE - MAX(t.transaction_date))         AS dormant_days,
    CASE
        WHEN (CURRENT_DATE - MAX(t.transaction_date)) > 180 THEN 'DORMANT'
        ELSE 'ACTIVE'
    END AS status
FROM depots d
JOIN sparkassen s ON d.sparkasse_id = s.sparkasse_id
LEFT JOIN transactions t ON d.depot_id = t.depot_id AND t.status = 'SETTLED'
GROUP BY d.depot_id, d.depot_number, s.sparkasse_name
ORDER BY dormant_days DESC NULLS FIRST;


-- ============================================================
-- Solution 8: Data Quality Checks
-- ============================================================
WITH issues AS (
    SELECT transaction_id, 'NEGATIVE_AMOUNT'    AS issue_type FROM transactions WHERE amount_eur <= 0
    UNION ALL
    SELECT transaction_id, 'SETTLEMENT_BEFORE_TRADE' FROM transactions
    WHERE settlement_date < transaction_date
    UNION ALL
    SELECT transaction_id, 'T3_BREACH'          FROM transactions
    WHERE settlement_date - transaction_date > 3
      AND status = 'SETTLED'
    UNION ALL
    SELECT transaction_id, 'NULL_NAV_SETTLED'   FROM transactions
    WHERE nav_price IS NULL AND status = 'SETTLED'
)
SELECT
    issue_type,
    COUNT(*)                                    AS issue_count,
    ARRAY_AGG(transaction_id ORDER BY transaction_id LIMIT 5) AS sample_txn_ids
FROM issues
GROUP BY issue_type
ORDER BY issue_count DESC;


-- ============================================================
-- Solution 9: Cumulative net inflow per fund
-- ============================================================
WITH daily_flows AS (
    SELECT
        f.fund_name,
        t.transaction_date                                           AS txn_date,
        SUM(CASE WHEN t.transaction_type = 'BUY'  THEN t.amount_eur
                 WHEN t.transaction_type = 'SELL' THEN -t.amount_eur
                 ELSE 0 END)                                         AS daily_net_flow
    FROM transactions t
    JOIN funds f ON t.fund_id = f.fund_id
    WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '12 months'
      AND t.status = 'SETTLED'
    GROUP BY f.fund_name, t.transaction_date
)
SELECT
    fund_name,
    txn_date,
    ROUND(daily_net_flow, 2)   AS daily_net_flow,
    ROUND(SUM(daily_net_flow) OVER (
        PARTITION BY fund_name
        ORDER BY txn_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2)                      AS cumulative_net_flow
FROM daily_flows
ORDER BY fund_name, txn_date;


-- ============================================================
-- Solution 10: Sparkasse performance ranking with RANK()
-- ============================================================
WITH sparkasse_aum AS (
    SELECT
        s.sparkasse_id,
        s.sparkasse_name,
        s.region,
        SUM(h.units * fn.nav_price)  AS total_aum
    FROM sparkassen s
    JOIN depots d    ON s.sparkasse_id = d.sparkasse_id AND d.active = TRUE
    JOIN holdings h  ON d.depot_id = h.depot_id
    JOIN fund_nav fn ON h.fund_id = fn.fund_id
                    AND fn.nav_date = (SELECT MAX(nav_date) FROM fund_nav WHERE fund_id = h.fund_id)
    GROUP BY s.sparkasse_id, s.sparkasse_name, s.region
),
sparkasse_inflow AS (
    SELECT
        d.sparkasse_id,
        SUM(CASE WHEN t.transaction_type = 'BUY'  THEN t.amount_eur
                 WHEN t.transaction_type = 'SELL' THEN -t.amount_eur
                 ELSE 0 END) AS net_inflow_12m
    FROM transactions t
    JOIN depots d ON t.depot_id = d.depot_id
    WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '12 months'
      AND t.status = 'SETTLED'
    GROUP BY d.sparkasse_id
),
sparkasse_depots AS (
    SELECT sparkasse_id, COUNT(*) AS active_depots
    FROM depots WHERE active = TRUE
    GROUP BY sparkasse_id
)
SELECT
    a.sparkasse_name,
    a.region,
    ROUND(a.total_aum, 2)             AS total_aum,
    ROUND(i.net_inflow_12m, 2)        AS net_inflow_12m,
    COALESCE(dp.active_depots, 0)     AS active_depots,
    RANK() OVER (PARTITION BY a.region ORDER BY a.total_aum DESC) AS region_aum_rank
FROM sparkasse_aum a
LEFT JOIN sparkasse_inflow i  ON a.sparkasse_id = i.sparkasse_id
LEFT JOIN sparkasse_depots dp ON a.sparkasse_id = dp.sparkasse_id
ORDER BY a.region, region_aum_rank;
