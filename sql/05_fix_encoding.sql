-- =============================================================
-- DekaBank Interview Prep: Fix German Character Encoding
-- =============================================================
-- Problem: German umlauts (ü, ö, ä) were corrupted to '??' when
-- the CSV/SQL was loaded without UTF-8 encoding set correctly.
--
-- Root cause: psql client encoding did not match database UTF-8.
--
-- HOW TO PREVENT THIS IN FUTURE:
--   Always connect with:  psql -U postgres --set=client_encoding=UTF8
--   Or run first:         SET client_encoding = 'UTF8';
--
-- Run this script to fix all broken names in the live database.
-- Safe to run multiple times (idempotent).
-- =============================================================

SET search_path TO deka;
SET client_encoding = 'UTF8';

-- -------------------------------------------------------------
-- Fix sparkassen names (sparkasse_name + city columns)
-- -------------------------------------------------------------
UPDATE sparkassen SET
    sparkasse_name = 'Stadtsparkasse München',
    city           = 'München'
WHERE sparkasse_code = 'SPK-MUC';

UPDATE sparkassen SET
    sparkasse_name = 'Stadtsparkasse Düsseldorf',
    city           = 'Düsseldorf'
WHERE sparkasse_code = 'SPK-DUS';

UPDATE sparkassen SET
    sparkasse_name = 'Kreissparkasse Böblingen',
    city           = 'Stuttgart'
WHERE sparkasse_code = 'SPK-STU';

UPDATE sparkassen SET
    sparkasse_name = 'Sparkasse Nürnberg',
    city           = 'Nürnberg'
WHERE sparkasse_code = 'SPK-NUE';

UPDATE sparkassen SET
    sparkasse_name = 'Sparkasse KölnBonn',
    city           = 'Köln'
WHERE sparkasse_code = 'SPK-KOL';

-- -------------------------------------------------------------
-- Fix fund names with special characters
-- -------------------------------------------------------------
UPDATE funds SET
    fund_name = 'Deka-BasisAnlage konservativ'
WHERE isin = 'DE000DK2CFT0';

UPDATE funds SET
    fund_name = 'Deka-BasisAnlage ausgewogen'
WHERE isin = 'DE000DK2CFU8';

UPDATE funds SET
    fund_name = 'Deka-BasisAnlage dynamisch'
WHERE isin = 'DE000DK2CFV6';

UPDATE funds SET
    fund_name = 'Deka-Nachhaltigkeit Aktien TF'
WHERE isin = 'DE000DK0LLA4';

UPDATE funds SET
    fund_name = 'DekaImmobilien Europa'
WHERE isin = 'DE000DK0M9W3';

-- -------------------------------------------------------------
-- Verify the fix
-- -------------------------------------------------------------
SELECT sparkasse_code, sparkasse_name, city
FROM sparkassen
ORDER BY sparkasse_id;

SELECT isin, fund_name
FROM funds
ORDER BY fund_id;

-- -------------------------------------------------------------
-- ALTERNATIVE: Nuclear option - re-seed from scratch
-- Only use if the above UPDATEs are not enough
-- -------------------------------------------------------------
-- DELETE FROM deka.sparkassen;
-- Then re-run 02_seed_data.sql with: SET client_encoding = 'UTF8'; at the top
