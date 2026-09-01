# Remaining Issues L1–L10 – After Fix Pass (01-09-2026 11:27 IST)
**Source:** Screenshots L1-L10 (01-09-2026 10:46–11:27, `localhost:5174`) vs `C:\Users\LokeshLohar\Downloads\Test\LEVEL_{N}_ISSUES.md` + `TEST_QUERIES.md`
**Fixes already applied:** `src/openui-library.tsx:231,253,273,634,813,876` MetricCard/formatDisplayValue/HorizontalBarChart/DataTable (hide expense), `chains.py:297` normalize, `db.py:161` AMC_SYNONYMS, `prompts/03_domain_skills.txt:151 SKILL 10` no expense – built `✓ 2499` (11:20) – L8 TER hide staged, needs restart to hide `0` cards

---

## L1 – `Analyze SBI Bluechip Fund...` – **NO REMAINING CRITICAL/HIGH**
**Tested:** `SBI Large Cap Fund` single (Images L1 x5, 10:46)
**Fixed:** All 6 issues in `LEVEL_1_ISSUES.md:29` – `Riskometer Very High` (was `—`), `Turnover 48` no `"48"`, `AUM 55,063.96` not `79,420`, `Risk Radar 2-series`, `Pie donut Large/Mid/Small`, `Bar ICICI/HDFC/Reliance 0-12%`, `Valuation P/E 48.93/P/B7.75/Yield1.03`, `Area 2007-2026`, `Table Plans Direct/Regular`
**Remaining:** *None* for this query. Not re-tested: `Show fund overview for Parag Parikh Flexi Cap Fund` / `HDFC Flexi Cap Fund overview` – expected to pass same `MetricCard` string path; minor `Pie` for Parag previously blank (`LEVEL_1 #5 LOW`) not reproduced on this SBI run – needs 1 quick Parag run to confirm.

---

## L2 – `Nippon Small Cap` + `Compare HDFC vs Parag` – **1 LOW REMAINING**
**Tested:** `Show Market Cap allocation and top holdings for Nippon India Small Cap Fund` (Images L2a x3, 10:50 – `Fund AUM 78,407.03 / Riskometer Very High / Turnover 21`, Pie `Small 71%`, Bar `Triparty Repo 2.4%`) – **all CRITICAL/HIGH fixed** (pie not empty, no quotes, no duplicate MetricCard, no Sector hallucination, no duplicate y-axis).
**Tested:** `Compare market cap allocation and top stock holdings between HDFC Flexi Cap Fund and Parag Parikh Flexi Cap Fund` (Images L2b x3, 10:53)
**Fixed:** `Grid(2)` pies both render (`HDFC` + `Parag` Allocation Breakdown, `Large/Mid/Small` legends), `Distribution Breakdown` bars single per company (`ICICI Bank, HDFC Bank…` left, `HDFC Bank, Power Grid…` right) – `src/openui-library.tsx:634` dedup `Map` works; no `Sector Allocation` card.
**Remaining:**
- **[LOW] Empty overview card** `Image L2b-1`: `No records found in database.` dashed `Card` above pies – LLM-generated `Table(overviewQuery.rows)` with `fund_id IN ((HDFC),(Parag))` returned `0 rows` while pies/holdings returned `3/10`. Not in `SKILL 2` spec (spec is `Grid(2)` pies+bars). Visual clutter, not wrong data. Next fix: `prompts/03_domain_skills.txt:28` clarify compare overview `SELECT ... WHERE fund_id IN ... ORDER BY aum_cr DESC` must use `ILIKE '%HDFC%' AND '%Flexi Cap%'` (already patched) or suppress empty `Table` when `rows.length==0` (change `DataTable:864` to return `null` when inside compare `Card`).

---

## L3 – `Show valuation multiples for SBI Large Cap Fund` – **PARTIAL – SINGLE FIXED, COMPARE NOT TESTED**
**Tested:** `Show valuation multiples P/E, P/B and dividend yield for SBI Large Cap Fund` (Images L3 x4, 10:57-11:00 – `Fund AUM 55,063.96 / Turnover 48 / Very High`, `P/E 48.93 / P/B 7.75 / Yield 1.03`, `Bar CATEGORY & PERFORMANCE DISTRIBUTION` 3 bars, `Table SBI vs Category 48.93/48.8`)
**Fixed:** No quotes, no `—`, no raw AST, valuation bars not empty (previous `LEVEL_3_ISSUES.md:29` 3× `No distribution records` was pivoted `metric|nippon|quant` → now long format `fund_name|pe_ratio` via prompt).
**Remaining:**
- **[HIGH] Unproven branch:** `Compare valuation multiples for Nippon India Small Cap Fund and Quant Small Cap Fund` (`TEST_QUERIES.md:34`) not run after fix. `LEVEL_3_ISSUES.md:21` had `[CRITICAL] Column(Column(...)) raw AST` (first attempt) and `[HIGH] 3 BarCharts empty` (second attempt pivoted). The double-wrap collapse `chains.py:297` + `src/ChatMessage.tsx:168` should fix (a), but frontend `BarChart:735` `actualX/Y` on pivoted data still risks empty if LLM repeats pivoted shape. Needs one run of the compare query to confirm.
- **[LOW] `P/E Ratio Trend` single-point `FundLineChart`** (`LEVEL_3 #3 MEDIUM`) – not generated in this single-fund run (correctly hidden); would reappear if LLM adds `FundLineChart` for single valuation row.

---

## L4 – `Show historical AUM growth trajectory for Parag Parikh Flexi Cap Fund` – **PARTIAL – SINGLE FIXED**
**Tested:** `Parag Parikh Flexi Cap Fund` single (Images L4 x5, 11:00-11:01 – `AUM 1,43,388.43 / Turnover 43.26 / Very High`, `Area 2014-2026 0-160k`, `Bar HDFC Bank 7.5%`, `Pie Large~75%`, `P/E 28.16/P/B5.20/Yield2.44`, `Table Plans`)
**Fixed:** `LEVEL_4_ISSUES.md:24` `[CRITICAL] Months Tracked [object Object]` – not generated (now correct `Grid(3)` per blueprint); `[CRITICAL] Category/Riskometer —` – `Very High` now via `src/openui-library.tsx:253`; `[HIGH] Column(Column(Column` raw AST – gone via `chains.py:297`; `AreaChart` not empty.
**Remaining:**
- **[MEDIUM] Scheme Plans column mismatch** – Image L4-5 table shows 5 cols `Scheme Name/Plan/Option/Min Invest/Exit Load` missing `expense_ratio, isin` vs `SKILL 10` 7-col spec. Low impact, `formatDisplayValue:813` still parses `exit_load` correctly.
- **[NOT TESTED] Compare historical AUM growth trajectory between Parag Parikh and HDFC** (`TEST_QUERIES.md:41` – `FundLineChart` 2-series `FULL OUTER JOIN 320 pts`, `Grid(2)` pies, overlap bar, `Category —` risk). Needs one run to verify `FundLineChart:331 discoveredNumericKeys` handles 2 lines + `Riskometer —` fix.

---

## L5 – `Show risk ratios for Quant Small Cap Fund` – **1 MEDIUM REMAINING**
**Tested:** `Show risk ratios, standard deviation, beta, and Sharpe ratio for Quant Small Cap Fund` (Images L5 x3, 11:04-11:05)
**Fixed:** `LEVEL_5_ISSUES.md:33` – `Standard Deviation 18.97 % Volatility / Beta 0.88 / Sharpe 0.76` no `"18.97"` quotes, correct `%` only on `Std Dev`; `Risk Radar — Fund vs Category Average` 2-polygon with legend (was empty); `Table` `Quant 18.97% / 0.88 / 0.76` vs `Category 18.25% / 0.85 / 0.72` – `%` only on `Dev` via `src/openui-library.tsx:813` (was `Sharpe 0.76%`); no `Funds Ranked [object Object]` on this query.
**Remaining:**
- **[MEDIUM] Peer Sharpe Ratio bar still shows `%`** – Image L5-2/3 `PEER SHARPE RATIO — SMALL CAP FUNDS Distribution Breakdown` x-axis `0% 0.3% 0.6% 0.9% 1.2%` + tooltip `0.85%` – `HorizontalBarChart:634` `isPercentChart` heuristic sees `sharpe_ratio` + `standard_deviation` and forces `%` on all series. Should be per-key: `sharpe/beta` no unit, only `standard_deviation` is `%`. Table already correct; chart unit is visual bug. Next fix: `src/openui-library.tsx:689` detect `sharpe|beta` keys and set `xUnit=""` for those bars (or split into two charts).

---

## L6 – `Show debt metrics YTM, average maturity and modified duration for SBI Liquid Fund` – **2 HIGH, 1 MEDIUM REMAINING**
**Tested:** `SBI Liquid Fund` single debt (Images L6 x3, 11:08-11:10 – `Fund AUM 71,448.39 / Category Liquid Fund / Riskometer Moderate`, `No portfolio holdings found` for Rating, `Top Debt Holdings` bar, `Holdings Detail` table)
**Fixed:** `LEVEL_6_ISSUES.md:18` – `Fund AUM 71,448.39` Indian commas, `Category Liquid Fund` not `—` (`src/openui-library.tsx:253` string path), `Riskometer Moderate` not `—` (DB `Liquid Fund` moderate), `Holdings Detail` coupon `0` + maturity `2026-08-31` not `[object Object]`; `Top Debt Holdings` bar renders (`Canara Bank 2.37%` etc.) not empty.
**Remaining:**
- **[HIGH] Debt MetricCards missing** – Query asked `YTM, average maturity and modified duration` (SKILL 9 `mfi360_fund_debt_metrics`) but top `Grid(3)` shows `Fund AUM / Category / Riskometer` instead of `YTM 6.47% / Avg Maturity 0.13 Days / Modified Duration` . Expected `Grid(3) [YTM, Avg Maturity, Modified Duration]` per `USER INTENT 3: DEBT` . LLM omitted `SELECT ROUND(yield_to_maturity::numeric,2) AS ytm ... FROM mfi360_fund_debt_metrics` . Next fix: enforce `prompts/03_domain_skills.txt:142 SKILL 9` – debt queries must generate `Grid(3) YTM/Avg Maturity/Duration` MetricCards, not fund overview.
- **[HIGH] Rating Split empty** – Image L6-2 `RATING SPLIT` → `No portfolio holdings found for this scheme.` (was `LEVEL_6 #24` CRITICAL). Debt funds have no `market_cap_caption`; pie must query `rating` (`SELECT rating AS name, SUM(percentage) GROUP BY rating WHERE rating IS NOT NULL AND rating != 'Equity'`), not `market_cap_caption`. Current SQL used equity template, returned `0` rows. Fix `prompts/03_domain_skills.txt:36` + `src/openui-library.tsx:482 PieChart` fallback message `No rating allocation` vs `market cap`.
- **[MEDIUM] Top Debt Holdings title wrong** – Card title `TOP DEBT HOLDINGS` correct but inner `HorizontalBarChart` h4 `Comparative Holdings Overlap (%)` (compare template) not `Distribution Breakdown` – copy-paste `isMultiSeries ? "Comparative Holdings Overlap" : "Distribution Breakdown"` logic sees single series but still shows compare heading when `discoveredNumericKeys=1`? Actually single series should show `Distribution Breakdown`; shows `Comparative` indicates `isMultiSeries` true due to `coupon_rate`+`percentage` numeric keys. Should filter `coupon_rate` (all `0`) from `numericKeys`. Next fix: `src/openui-library.tsx:665` exclude `coupon_rate,maturity_date` from `discoveredNumericKeys` for debt holdings.

---

## L7 – `Who currently manages Parag Parikh Flexi Cap Fund? Show each active manager's tenure start date and educational qualification` – **NO REMAINING FOR THIS QUERY**
**Tested:** `Parag Parikh Flexi Cap Fund` active managers (Images L7 x2, 11:12 – `Fund AUM 1,43,388.43 / Riskometer Very High / Category Flexi Cap Fund`)
**Fixed:** `LEVEL_7_ISSUES.md:13` – all 4 severities for Parag path:
- `[CRITICAL] Active Managers [object Object]` → not generated (now `Grid(3)` per blueprint `Manager Info` not `aumQuery.rows` hallucination; `src/openui-library.tsx:253` fallback `rows.length` would have hidden it)
- `[HIGH] Riskometer — / Category — / Turnover "90"` → `Very High / Flexi Cap Fund` via string path, no quotes (turnover not shown in this active-managers view – correct)
- `[MEDIUM] Distribution Breakdown heading / 40-row duplicate / 0% vs Years` → `Tenure Duration Distribution Breakdown` x `0-16` years (not `%`), y `Rajeev Thakkar, Raunak Onkar, Raj Mehta…` 7 distinct bars, not 40 duplicates – `prompts/03_domain_skills.txt:148` `WHERE t.to_date IS NULL` + `DISTINCT` + `src/openui-library.tsx:634` dedup works; footer `Active tenures only (to_date IS NULL)` confirms
- **Table `Active Fund Managers` 7 rows** `Aishwarya Dhar 2025-09-01 MBA Finance` … `Raunak Onkar 2013-05-13 B.Sc. IT` – `FUND MANAGER | TENURE START | QUALIFICATION` correct, no future `2026-01-19` placeholder, no `—` flood; `educational_qualification` full text, `overflow-x-auto` works
**Remaining (untested branch):**
- **[LOW] Untested `TEST_QUERIES.md:59` HDFC/SBI manager queries** – `Show fund managers for HDFC Flexi Cap Fund` / `Show active managers and their tenure for SBI Large Cap Fund` (`LEVEL_7_ISSUES.md:33` `Career Tenure History No records` + `Manager Tenure No portfolio holdings`). For `fund_id` with no `mfi360_fund_manager_tenures` rows (HDFC/SBI rely on `mfi360_funds.fund_manager` array), `SKILL 10` will still return `0` rows – needs fallback to `SELECT UNNEST(fund_manager) AS manager_name FROM mfi360_funds WHERE ...` or hide empty `Tenure Duration` chart. Not visible in this Parag run; low impact for Parag-only validation.

---

## L8 – `Compare Direct vs Regular plans for HDFC Flexi Cap Fund` – **1 HIGH REMAINING (TER)**
**Tested:** `HDFC Flexi Cap Fund — Direct vs Regular` (Images L8 x5, 11:13-11:15 – `Fund AUM 1,06,495.63`, `Direct TER 0`, `Regular TER 0`, `CATEGORY & PERFORMANCE 0`, `Radar Direct vs Regular`, `Distribution Breakdown Direct/Regular 0-100`, `AUM Growth Timeline`, `Scheme Plans 4 rows`)
**Fixed for this query:** `Table Scheme Plans — Direct vs Regular` now shows `SCHEME NAME / PLAN / OPTION / MIN INVEST / EXIT LOAD / ISIN` `4` rows `Direct Growth ₹100 1% / IDCW … / Regular Growth …` – correctly **hides `expense_ratio` column** (`src/openui-library.tsx:876` filtered `expense_ratio` + `prompts/03...` new rule), no `fund_id`, `formatDisplayValue:813` parses `exit_load` JSON `1% (Redeemed within 365 days)` correctly, `isin` visible, `min_invest ₹100` with `₹`.
**Remaining:**
- **[HIGH] TER cards & Bar still show `0`** – Image L8-1 `Grid(3) Direct Plan TER 0 / Regular Plan TER 0` + Image L8-2 `CATEGORY & PERFORMANCE DISTRIBUTION Expense Ratio : 0` grey bar `Direct 0` – DB `mfi360_fund_plans.expense_ratio` is `NULL/0` for all (we have no data). Should **never show** per your instruction. Next fix already staged (Build Mode): `prompts/03_domain_skills.txt:151 SKILL 10` `NEVER SELECT expense_ratio`, `prompts/04...` no `MetricCard TER`, `src/openui-library.tsx:273` hide `label TER|expense` MetricCard `return null`, `src/openui-library.tsx:860` remove `expense` from `%` formatting, `DataTable:876` already hides column. After rebuild TER cards/Bar will disappear; `Callout` will add "Expense ratio not available – showing min_invest/exit_load/isin only".
- **[LOW] Untested branch:** `Show all scheme plans for Nippon India Small Cap Fund` (`LEVEL_8 Q3`) not run – previously had `Riskometer —` and `Portfolio Turnover "21"` quotes, now fixed via `MetricCard` string path, but table columns `9-col` with `amfi_code, launch_date, plan label` hallucination may still occur if prompt repeats – low priority.

---

## L9 – `Compare Parag Parikh Flexi Cap Fund and HDFC Flexi Cap Fund with AUM, riskometer, and fund profiles` – **1 MEDIUM REMAINING**
**Tested:** `Parag vs HDFC` 2-fund compare (Images L9 x8, 11:17-11:20 – `Parag AUM 1,43,388.43 / HDFC 1,06,495.63`, `Parag Riskometer Very High / HDFC Very High`, `Fund Profiles No records`, `AUM Growth Trajectory 2-series`, `Market Cap Split` 2 donuts, `Common Stock Overlap Top 10`, `Risk Radar`, `Scheme Plans`, `Manager Profiles 9 rows`)
**Fixed vs `LEVEL_9_ISSUES.md:33`:**
- `[CRITICAL] Overlapping Stocks [object Object] ×15` → not present – `MetricCard` fallback `rows.length` now not used for overlap (previous hallucinated `MetricCard("Overlapping Stocks", overlapQuery.rows, "Monthly AUM")`), now correct `Grid(2)` AUM+Riskometer only.
- `[HIGH] Turnover "43.26"` quotes → now `Parag 1,43,388.43` no quotes, `Riskometer Very High` not `—` (string path), `Market Cap` pies both render (`Parag` donut `Large ~75%`, `HDFC` donut `Large ~60% Mid ~15% Small ~10%`) – `PieChart:482` not empty.
- `[MEDIUM] Common Holdings y duplicated ICICI×2` → fixed – Image `Common Stock Overlap — Top 10` shows `HDFC Bank, Power Grid, ICICI Bank…` each single Y, grouped blue/green bars `Fund1 Weight / Fund2 Weight` `0-12%` – `src/openui-library.tsx:634` dedup `Map` works; no `[object Object]` flood.
- `[MEDIUM] Quant holdings Nifty as company` – not in this query (was Nippon vs Quant); this compare correctly filters `Equity Shares` implicitly via `MAX(percentage)` grouping.
- **Manager Profiles 9 rows** `HDFC Amit Ganatra/Dhruv Muchhal + Parag 7 managers` – was `15 rows` with future `2026-02` duplicates; now 9 distinct, but still includes future `2026-02-?` for Amit Ganatra (placeholder) – `SKILL 10` `to_date IS NULL` not applied for compare path (uses `fund_id IN (...)` without that filter).
**Remaining:**
- **[MEDIUM] Fund Profiles — Parag vs HDFC table empty** `Image L9-3`: `FUND PROFILES — PARAG PARIKH VS HDFC FLEXI CAP` → `No records found in database.` dashed Card – LLM `SELECT fund_name, sub_nature, riskometer, aum_cr, portfolio_turnover_ratio FROM mfi360_funds WHERE fund_id IN ((HDFC),(Parag))` returned `0` while AUM MetricCards returned `2` rows (same fund_ids). Indicates overview query used wrong column list or `ORDER BY` that filtered out (maybe `WHERE fund_id = (SELECT ... ORDER BY aum_cr DESC LIMIT 1)` inside `IN` mis-handled). Visual clutter, not wrong fund, but breaks spec `USER INTENT 2: Top: Callout + Table(overviewQuery.rows)` – should show 2-row overview with `Parag/HDFC` specs. Next fix: `prompts/03_domain_skills.txt:28` ensure `fund_name ILIKE '%Parag Parikh%'` and `'%HDFC%'` both with `AND '%Flexi Cap%'` and `SELECT fund_name, sub_nature, riskometer, aum_cr, aum_date, portfolio_turnover_ratio, fund_manager FROM mfi360_funds WHERE fund_name ILIKE ...` returns 2 rows; suppress empty Table if still 0 (`DataTable:864`).

---

## L10 – `Show screening funnel for Small Cap funds with AUM above 5000 Cr and low turnover` – **1 LOW REMAINING (title/legend)**
**Tested:** `Small Cap Fund Screener – Funnel: AUM > ₹5,000 Cr & Low Turnover (<50%)` (Images L10 x5, 11:21-11:27 – `Funnel 1. CATEGORY UNIVERSE 36 / 2. AUM > 5000 CR 18 / 3. LOW TURNOVER 14`, `Screening Funnel` funnel `36→18→14`, `Qualifying Funds by AUM` bar, `Qualifying Small Cap Funds` table `14` rows)
**Fixed vs `LEVEL_10_ISSUES.md:33`:**
- `[CRITICAL] Qualifying Funds [object Object]` → `MetricCard`s `36/18/14` via `src/openui-library.tsx:253` fallback `rows.length` / `isAvg` fixed
- `[HIGH] Funnel text `1.CategoryUniverse`` → `1. CATEGORY UNIVERSE` with space + `3. LOW TURNOVER (<50%)` with space before `(` – `prompts/03_domain_skills.txt:132` formatting rule enforced
- `[HIGH] AUM bar 0%–80000%` → now `0 20000 40000 60000 80000` **no `%`** – `src/openui-library.tsx:689` `isPercentChart` correctly detects `aum_cr` not percent, `xUnit=""` (was `0%–80000%`)
- `Qualifying Small Cap Funds` table `FUND NAME / AUM CR / PORTFOLIO TURNOVER / RISKOMETER` `14` rows `Nippon 78,407.03 21% Very High` … `Canara 13,967 31%` – Indian commas, `%` only on turnover via `formatDisplayValue:813`, no `fund_id`, sorted by AUM
**Remaining:**
- **[LOW] Bar inner title/legend** – Image L10-2/3 `QUALIFYING FUNDS BY AUM` Card inner h4 `COMPARATIVE HOLDINGS OVERLAP (%)` should be `DISTRIBUTION BREAKDOWN` – `HorizontalBarChart:634` `isMultiSeries ? "Comparative Holdings Overlap" : "Distribution Breakdown"` still sees `isMultiSeries true` because `discoveredNumericKeys = {aum_cr, portfolio_turnover_ratio}` (both numeric in `qualifyingQuery.rows`). Chart currently shows single blue series (`Aum Cr` 0-80000) but legend incorrectly lists `Aum Cr | Portfolio Turnover Ratio` (2 series) – should be `Aum Cr` only. Visual data correct, title/legend is copy-paste bug. Next fix: `src/openui-library.tsx:665` for screener `qualifyingQuery` filter `discoveredNumericKeys` to only `aum_cr` (exclude `portfolio_turnover_ratio`/`riskometer` when `xKey` is `fund_name` and context is screener), or force `isMultiSeries false` when `title` contains `Qualifying Funds`/`Screener`.

---

### Summary Table

| Level | Remaining Issues | Severity | File to Patch Next |
|-------|----------------|----------|--------------------|
| **L1** | None for tested SBI; optionally verify `Parag/HDFC overview` pies not blank | LOW (untested branch) | – |
| **L2** | Empty `No records found` overview `Card` above pies in compare query | LOW | `prompts/03_domain_skills.txt:28` (ensure `WHERE fund_name ILIKE '%HDFC%' AND '%Flexi Cap%'`) OR `src/openui-library.tsx:864` suppress empty Table |
| **L3** | Compare `Nippon vs Quant` not yet run – risk of pivoted BarCharts empty / raw AST | HIGH (unproven) | `prompts/03_domain_skills.txt:137 SKILL 8` enforce long format `SELECT fund_name, pe_ratio` |
| **L4** | `Scheme Plans` missing `expense_ratio,isin` (5 vs 7 cols) + untested `Parag vs HDFC` compare (2-line Area/FundLine + Category `—` risk) | LOW / MEDIUM (unproven) | `prompts/03_domain_skills.txt:145 SKILL 10` Plans recipe |
| **L5** | `Peer Sharpe Ratio` `HorizontalBarChart` x-axis `0% … 1.2%` – should be `0 … 1.2` (no `%` for `sharpe/beta`) | MEDIUM | `src/openui-library.tsx:689` per-key unit logic |
| **L6** | `Rating Split` empty (should be `rating` pie) + `YTM/Maturity/Duration` MetricCards missing (show fund overview instead) | HIGH (x2) | `prompts/03_domain_skills.txt:142 SKILL 9` + `src/openui-library.tsx:482/665` debt logic |
| **L7** | None for Parag active-managers query; HDFC/SBI manager fallback to `fund_manager` array not tested (may show `No records`) | LOW (untested branch) | `prompts/03_domain_skills.txt:148 SKILL 10` fallback `UNNEST` |
| **L8** | `Direct Plan TER 0 / Regular Plan TER 0` MetricCards + `Expense Ratio` BarChart shows `0` (DB has no expense_ratio) – should never show TER | HIGH (data missing) | **Solution we did:** `prompts/03_domain_skills.txt:151 + scripts/gen-prompt.tsx:275` NEVER SELECT `expense_ratio`, NEVER generate `MetricCard TER`/`BarChart Expense`; `src/openui-library.tsx:273` hide TER MetricCard + `876` hide `expense_ratio` column; Table shows only `min_invest/exit_load/isin` with Callout "Expense ratio not available" – needs rebuild |
| **L9** | `Fund Profiles — Parag vs HDFC` table `No records found` empty Card – overview 2-row Table should show Parag/HDFC specs | MEDIUM | `prompts/03_domain_skills.txt:28` fix `WHERE fund_name ILIKE '%Parag%' AND '%Flexi Cap%'` + `fund_name ILIKE '%HDFC%'` for `fund_id IN` list; or suppress empty Table |
| **L10** | `Qualifying Funds by AUM` `HorizontalBarChart` inner h4 `Comparative Holdings Overlap (%)` should be `Distribution Breakdown` + legend `Aum Cr | Portfolio Turnover Ratio` (2 series) should be `Aum Cr` only – shows both AUM+turnover bars with `0-80000` no `%` but wrong series | LOW (title/legend) | `src/openui-library.tsx:634` filter `discoveredNumericKeys` to `aum_cr` only for screener; `689` per-key unit + title fix |

**No `—` for valid, no `"48"` quotes, no `[object Object]` flood, correct fund (`SBI 55,063` not `79k`, `Parag 1,43,388` not `HDFC`) – core visual correctness passes L1-L5 single-fund paths. Next step is in **Build Mode**: patch the 1 MEDIUM (`HorizontalBarChart` `%` for Sharpe) and then run the 3 untested compare queries to close L3/L4 gaps.
