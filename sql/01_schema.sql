-- =============================================================
-- DekaBank Interview Prep: Database Schema
-- PostgreSQL 15+
-- =============================================================

DROP SCHEMA IF EXISTS deka CASCADE;
CREATE SCHEMA deka;
SET search_path TO deka;

-- -------------------------------------------------------------
-- 1. SPARKASSEN (Savings Banks - sales partners)
-- -------------------------------------------------------------
CREATE TABLE sparkassen (
    sparkasse_id    SERIAL PRIMARY KEY,
    sparkasse_code  VARCHAR(10)  NOT NULL UNIQUE,
    sparkasse_name  VARCHAR(100) NOT NULL,
    region          VARCHAR(50)  NOT NULL,
    city            VARCHAR(50)  NOT NULL,
    active          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------------
-- 2. FUNDS (Investment products with ISIN)
-- -------------------------------------------------------------
CREATE TABLE funds (
    fund_id         SERIAL PRIMARY KEY,
    isin            CHAR(12)     NOT NULL UNIQUE,
    fund_name       VARCHAR(100) NOT NULL,
    fund_type       VARCHAR(30)  NOT NULL CHECK (fund_type IN ('EQUITY','BOND','MIXED','MONEY_MARKET','REAL_ESTATE')),
    currency        CHAR(3)      NOT NULL DEFAULT 'EUR',
    ter             NUMERIC(5,4),  -- Total Expense Ratio e.g. 0.0145
    inception_date  DATE         NOT NULL,
    active          BOOLEAN      NOT NULL DEFAULT TRUE
);

-- -------------------------------------------------------------
-- 3. CUSTOMERS
-- -------------------------------------------------------------
CREATE TABLE customers (
    customer_id     SERIAL PRIMARY KEY,
    customer_code   VARCHAR(20)  NOT NULL UNIQUE,
    sparkasse_id    INT          NOT NULL REFERENCES sparkassen(sparkasse_id),
    first_name      VARCHAR(50)  NOT NULL,
    last_name       VARCHAR(50)  NOT NULL,
    date_of_birth   DATE         NOT NULL,
    customer_since  DATE         NOT NULL,
    risk_profile    VARCHAR(20)  NOT NULL CHECK (risk_profile IN ('CONSERVATIVE','BALANCED','GROWTH','AGGRESSIVE')),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------------
-- 4. DEPOTS (Custody accounts)
-- -------------------------------------------------------------
CREATE TABLE depots (
    depot_id        SERIAL PRIMARY KEY,
    depot_number    VARCHAR(20)  NOT NULL UNIQUE,
    customer_id     INT          NOT NULL REFERENCES customers(customer_id),
    sparkasse_id    INT          NOT NULL REFERENCES sparkassen(sparkasse_id),
    depot_type      VARCHAR(20)  NOT NULL CHECK (depot_type IN ('STANDARD','VL','RIESTER','BETRIEBLICH')),
    opened_date     DATE         NOT NULL,
    closed_date     DATE,
    active          BOOLEAN      NOT NULL DEFAULT TRUE
);

-- -------------------------------------------------------------
-- 5. FUND NAV (Daily Net Asset Values)
-- -------------------------------------------------------------
CREATE TABLE fund_nav (
    nav_id          SERIAL PRIMARY KEY,
    fund_id         INT          NOT NULL REFERENCES funds(fund_id),
    nav_date        DATE         NOT NULL,
    nav_price       NUMERIC(12,4) NOT NULL CHECK (nav_price > 0),
    UNIQUE (fund_id, nav_date)
);

CREATE INDEX idx_fund_nav_date ON fund_nav(nav_date);
CREATE INDEX idx_fund_nav_fund ON fund_nav(fund_id);

-- -------------------------------------------------------------
-- 6. HOLDINGS (Current positions per depot)
-- -------------------------------------------------------------
CREATE TABLE holdings (
    holding_id           SERIAL PRIMARY KEY,
    depot_id             INT            NOT NULL REFERENCES depots(depot_id),
    fund_id              INT            NOT NULL REFERENCES funds(fund_id),
    units                NUMERIC(15,6)  NOT NULL DEFAULT 0,
    avg_purchase_price   NUMERIC(12,4),
    last_updated         TIMESTAMP      NOT NULL DEFAULT NOW(),
    UNIQUE (depot_id, fund_id)
);

-- -------------------------------------------------------------
-- 7. TRANSACTIONS
-- -------------------------------------------------------------
CREATE TABLE transactions (
    transaction_id      SERIAL PRIMARY KEY,
    depot_id            INT            NOT NULL REFERENCES depots(depot_id),
    fund_id             INT            NOT NULL REFERENCES funds(fund_id),
    transaction_date    DATE           NOT NULL,
    settlement_date     DATE,
    transaction_type    VARCHAR(10)    NOT NULL CHECK (transaction_type IN ('BUY','SELL','SWITCH_IN','SWITCH_OUT','DIVIDEND')),
    units               NUMERIC(15,6)  NOT NULL,
    nav_price           NUMERIC(12,4),
    amount_eur          NUMERIC(15,2)  NOT NULL,
    fee_eur             NUMERIC(10,2)  NOT NULL DEFAULT 0,
    status              VARCHAR(15)    NOT NULL DEFAULT 'SETTLED' CHECK (status IN ('PENDING','SETTLED','CANCELLED','FAILED')),
    created_at          TIMESTAMP      NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_txn_date        ON transactions(transaction_date);
CREATE INDEX idx_txn_depot       ON transactions(depot_id);
CREATE INDEX idx_txn_fund        ON transactions(fund_id);
CREATE INDEX idx_txn_type_date   ON transactions(transaction_type, transaction_date);

-- -------------------------------------------------------------
-- Helpful view: depot with sparkasse and customer info
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_depot_detail AS
SELECT
    d.depot_id,
    d.depot_number,
    d.depot_type,
    c.customer_id,
    c.customer_code,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.risk_profile,
    s.sparkasse_id,
    s.sparkasse_code,
    s.sparkasse_name,
    s.region,
    d.opened_date,
    d.active
FROM depots d
JOIN customers c ON d.customer_id = c.customer_id
JOIN sparkassen s ON d.sparkasse_id = s.sparkasse_id;

-- -------------------------------------------------------------
-- Helpful view: current AuM per depot
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_aum_per_depot AS
SELECT
    h.depot_id,
    d.depot_number,
    s.sparkasse_name,
    s.region,
    SUM(h.units * fn.nav_price) AS total_aum_eur,
    COUNT(DISTINCT h.fund_id)   AS fund_count
FROM holdings h
JOIN depots d       ON h.depot_id = d.depot_id
JOIN sparkassen s   ON d.sparkasse_id = s.sparkasse_id
JOIN fund_nav fn    ON h.fund_id = fn.fund_id
                    AND fn.nav_date = (SELECT MAX(nav_date) FROM fund_nav WHERE fund_id = h.fund_id)
GROUP BY h.depot_id, d.depot_number, s.sparkasse_name, s.region;
