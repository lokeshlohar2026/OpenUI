# MF Saarthi OpenUI – Full Project Test Suite
# Paste each query one-by-one in the frontend (http://localhost:5174) and verify the visualization renders.
# DB verified 31-08-2026: 2061 funds, 9.6M holdings, 206k AUM history, 2011 valuations, 5735 risk ratios
# All fund names below are live in DB (ordered by AUM where relevant).

## How to Test
1. Run backend: `python main.py` (8001) and frontend `npm run dev` (5174)
2. Paste query exactly as written, press Enter
3. Check “Expected” – if `—` or empty, screenshot and check `logs/db.log` / `logs/llm.log`

---

### LEVEL 1 – Basic Single Fund Overview (MetricCard + Table)
**Tests:** `mfi360_funds`, `mfi360_fund_plans` | Visual: `Grid(3) MetricCard`, `Table`
1. `Show me SBI Large Cap Fund overview with AUM and riskometer`
   - Expected: MetricCard `Fund AUM ~55,063 Cr, Riskometer Very High`, Table `SBI Large Cap Fund`
2. `Analyze SBI Bluechip Fund with portfolio allocation, valuation multiples and AUM history`  # previous failing query – must now show Live Engine dashboard, not `—`
   - Expected: Same as SBI Large Cap (Bluechip → Large Cap synonym), Grid(3) AUM/Turnover/P/E, Pie + Bar, Area
3. `Show fund overview for Parag Parikh Flexi Cap Fund`
4. `Show HDFC Flexi Cap Fund overview`

### LEVEL 2 – Portfolio Holdings & Market Cap Allocation (Holdings Visuals)
**Tests:** `mfi360_fund_portfolio_holdings` | Visual: `PieChart(market_cap_caption)` + `HorizontalBarChart(company_name, percentage_in_net_asset)` in `Grid(2)`
5. `Show Market Cap allocation and top holdings for Nippon India Small Cap Fund`
   - Expected: Pie `Large 12% / Mid 13% / Small 71%`, Bar top 10 e.g. Triparty Repo, HDFC Bank
6. `Show top 10 holdings for HDFC Flexi Cap Fund`
7. `Show portfolio holdings and market cap allocation for ICICI Prudential Large Cap Fund`
8. `Compare market cap allocation and top stock holdings between HDFC Flexi Cap Fund and Parag Parikh Flexi Cap Fund` # Grid(2) 2 pies + holdings

### LEVEL 3 – Valuation Multiples (P/E, P/B, Dividend Yield)
**Tests:** `mfi360_scheme_valuation_metrics` | Visual: `Grid(3) MetricCard("P/E"/"P/B"/"Dividend Yield")`
9. `Show valuation multiples P/E, P/B and dividend yield for SBI Large Cap Fund`
   - Expected: MetricCards `P/E 48.93, P/B 7.75, Yield 1.03`
10. `Compare valuation multiples for Nippon India Small Cap Fund and Quant Small Cap Fund`
11. `Show average market cap and valuation for Templeton India Value Fund`

### LEVEL 4 – Historical AUM Wealth Growth (Time-Series)
**Tests:** `mfi360_fund_aum_history` | Visual: `AreaChart(aum_date, aum_cr)` full width + `FundLineChart` for 2 funds
12. `Show historical AUM growth trajectory for Parag Parikh Flexi Cap Fund`
   - Expected: AreaChart 158 points, latest ~143k Cr
13. `Compare historical AUM growth trajectory between Parag Parikh Flexi Cap Fund and HDFC Flexi Cap Fund`
   - Expected: FundLineChart 2 lines `f1_aum/f2_aum` via FULL OUTER JOIN, 320 points
14. `Show AUM history for Nippon India Small Cap Fund`

### LEVEL 5 – Risk & Volatility (Radar)
**Tests:** `mfi360_scheme_risk_ratios` + `mfi360_fund_plans` | Visual: `RadarChart(sharpe, beta, std_dev)` + `HorizontalBarChart`
15. `Show risk ratios, standard deviation, beta, and Sharpe ratio for Quant Small Cap Fund`
16. `Compare Quant Small Cap Fund with the Small Cap category average on risk ratios` # Skill 5: fund_risk + cat_risk UNION
17. `Show risk ratios for Baroda BNP Paribas Large Cap Fund – Direct Growth`
   - Expected: Radar + Table `sharpe 0.54, beta 0.94, std 13.68`

### LEVEL 6 – Debt & Fixed Income Analytics (YTM, Maturity, Duration)
**Tests:** `mfi360_fund_debt_metrics` | Visual: `Grid(3) MetricCard(YTM/Maturity/Duration)` + `PieChart(rating)` + `Table(coupon)`
18. `Show debt metrics YTM, average maturity and modified duration for SBI Liquid Fund`
19. `Analyze SBI Liquid Fund with debt holdings and YTM`
   - Expected: YTM ~6.5, Maturity 40 days, Duration 40 days (from `Franklin India Liquid Fund` sample, SBI Liquid similar)
20. `Compare debt metrics for Franklin India Liquid Fund and UTI Medium to Long Duration Fund`

### LEVEL 7 – Fund Managers & Tenures
**Tests:** `mfi360_fund_manager_tenures` + `mfi360_fund_managers` | Visual: `Table(manager_name, educational_qualification, from_date, to_date)`
21. `Who currently manages Parag Parikh Flexi Cap Fund? Show each active manager's tenure start date and educational qualification`
22. `Show fund managers for HDFC Flexi Cap Fund`
23. `Show active managers and their tenure for SBI Large Cap Fund`

### LEVEL 8 – Scheme Plans & Expense Ratios (Direct vs Regular)
**Tests:** `mfi360_fund_plans` | Visual: `Table(plan, option, expense_ratio, min_invest, isin, exit_load)` + `BarChart(expense_ratio)`
24. `Compare Direct vs Regular plans, expense ratios, and exit loads for Mirae Asset Large Cap Fund` # actually Mirae not in top, use HDFC Flexi Cap as reliable
25. `Compare Direct vs Regular plans for HDFC Flexi Cap Fund`
26. `Show all scheme plans for Nippon India Small Cap Fund`

### LEVEL 9 – Two-Fund Deep Comparison & Overlap
**Tests:** Holdings overlap, AUM compare, Risk Radar | Visual: `Grid(2) Pie + Pie`, `HorizontalBarChart(overlap)`, `FundLineChart`, `RadarChart`
27. `Compare Parag Parikh Flexi Cap Fund and HDFC Flexi Cap Fund with AUM, riskometer, and fund profiles`
28. `Show overlapping stock holdings between HDFC Flexi Cap Fund and Parag Parikh Flexi Cap Fund` # With h1/h2 CTE, 10-15 common stocks
29. `Compare Nippon India Small Cap Fund vs Quant Small Cap Fund with valuation and risk`

### LEVEL 10 – Screening & Funnel (Screener Visuals)
**Tests:** `mfi360_funds` counts | Visual: `FunnelChart(name, value)` + `HorizontalBarChart(qualifying)` + `Table`
30. `Show screening funnel for Small Cap funds with AUM above 5000 Cr and low turnover` # Skill 7: 1. Universe 36, 2. AUM>5000, 3. Turnover<50%
31. `Show funnel for Flexi Cap funds with AUM > 40000 Cr`
32. `Find Large Cap funds with turnover < 50% and AUM > 30000 Cr`

### LEVEL 11 – Advanced / Stress & Edge Cases
**Tests:** Joins, explanation, error handling | Visual: `Card`, `Callout`, `Table`, should not `—`
33. `List top 5 funds by AUM in Flexi Cap category`
   - Expected: Table Parag Parikh 143k, HDFC 106k, etc.
34. `Show funds with highest portfolio turnover ratio`
35. `Explain SBI Large Cap Fund vs category average – is it less volatile?` # Tests category average logic
36. `What is the expense ratio and exit load for SBI Large Cap Fund – Direct Growth vs Regular Growth?` # Tests JSON exit_load parsing
37. `Show benchmark for SBI Large Cap Fund` # Tests `amfi_fund_benchmarks` join (may be sparse, should show EmptyState not crash)

### LEVEL 12 – Synonym & Typo Resilience (Auto-Healer)
**Tests:** `db.py:COLUMN_ALIAS_MAP` + `AMC_SYNONYMS` + fuzzy match | Visual: Should still render despite typos
38. `Show holdings for hdfc flexi cap fund using weight and pe`  # weight→percentage_in_net_asset, pe→price_to_earnings
39. `Analyze SBIBLUECHIP fund`  # no space, should map via \bblue\s*chip\b → Large Cap
40. `Show PPFAS flexi cap fund holdings`  # PPFAS → Parag Parikh
41. `Compare absl small cap vs nippon small cap`  # ABSL → Aditya Birla Sun Life

---

## Expected Visual Checklist per Query
- **MetricCard** must show number (e.g., `55,063.96`) not `—` or `NaN` – if `—`, check `logs/llm.log` for `@Sum` hallucination or `chains.py:330` sanitizer.
- **PieChart** needs `name/value` with `>1` positive slice, else falls back to Bar/Table.
- **HorizontalBarChart** must show `company_name` y-axis, `%` x-axis.
- **AreaChart/FundLineChart** must have `date` x-axis, `aum` y-axis, 0.5s loading spinner then curve.
- **RadarChart** must have 2 series (fund vs category) when `vs category average` asked.
- **Table** must not show `fund_id/scheme_id`, must auto-prune 100% NULL cols, format `exit_load` JSON → `1% (within 30 days)` and `aum_cr` → `₹ 55,063 Cr`.

Run `python scripts/check-models.py` first to confirm Go models are `PASS`, then paste queries sequentially. If any visual shows `No matching records`, the SQL likely returned 0 rows – check `logs/db.log` for `rows: 0` and verify fund name exists via `SELECT fund_name FROM mfi360_funds WHERE fund_name ILIKE '%<name>%'`.

