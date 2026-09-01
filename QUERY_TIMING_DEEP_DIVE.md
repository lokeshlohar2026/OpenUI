# Query → Visualization Timing – Deepest Component Breakdown (Last 15 Queries)
**Generated:** 2026-09-01 11:55 IST | **Workspace:** `D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test` | **Mode:** `build` | **Prompt:** `openui_prompt.txt 51303 chars ~12825 tokens (01_library_ast 14k + 02_db_schema 19.5k + 03_domain_skills 13.9k + 04_syntactic 3.6k)` | **LLM:** `OPENCODE_MODEL=deepseek-v4-flash` via `chains.py:327 stream_openui_chain` (`opencode/mimo-v2.5-pro` / `groq/openai/gpt-oss-120b` / `gemini-3.6-flash`) | **DB:** `db.py:265 execute_safe_sql` `ThreadedConnectionPool 10` `statement_timeout 2000ms` | **Frontend:** `src/ChatMessage.tsx:196 toolProvider` → `main.py:49 /api/tools/sql_query` → `Renderer` + `myLibrary`
**Logs inspected:** `logs/llm.log` `[LLM CALL: SUCCESS]`, `logs/db.log` `[DB QUERY: SUCCESS/CACHED]`, `logs/app.log` `[INFO] DB [SUCCESS]` – last 15 queries `10:47-11:47` (today)

## TL;DR – Who Takes How Much? (small-to-small)
| Component | File:Line | Per-query time | % of end-to-end | What / Why |
|---|---|---|---|---|
| **Prompt load** | `chains.py:46 load_system_prompt()` + `scripts/gen-prompt.tsx:322` | `~2ms` cached after first load ( `PROMPTS_DIR` read once ) | `0.0%` | `01+02+03+04 → 51k` assembled; `load_table_schema_map:83` `information_schema.columns` cached in `_TABLES_MAP` |
| **LLM streaming** | `chains.py:186 stream_opencode` → `https://opencode.ai/zen/go/v1/chat/completions` `temperature 0.2 stream:true` | **`14.7s – 96.0s` median `43.9s` avg `52s`** | **`98%`** | System `12.8k tokens` + user `~15 tokens` → generate `400-900 tokens` (`Query()` ×120 + `MetricCard` etc). `deepseek-v4-flash` `~80 tok/s` + `Groq 429 retry 2.5s (chains.py:78)` + CoT for `FULL OUTER JOIN`/`GROUP BY` |
| **AST post-process** | `chains.py:210 reorder_ast` + `273 normalize_ast_root` + `src/ChatMessage.tsx:168 rewriteMacros/topologicalSort` | `<1ms` | `0.0%` | `reorder Query()→top, root→bottom; collapse Column(Column( → Column(; unwrap Column(var); sanitize @Max→"—"` |
| **DB – all parallel Query()** | `main.py:58 execute_safe_sql` → `db.py:313 LIMIT` → `psycopg2` | **`~35ms` avg per `sql_query`, `~140-280ms` wall (parallel) `0.14-0.28s`** | **`0.7%`** | `mfi360_funds ILIKE + ORDER BY aum_cr DESC LIMIT 1` (index), `holdings 9.5M` `GROUP BY market_cap` `~48ms`, `aum_history 246 rows ~42ms`, `risk UNION ~45ms`; `QUERY_CACHE_TTL 300s` → `0.05ms` on repeat |
| **Frontend render** | `src/openui-library.tsx:421 FundLineChart` `634 HorizontalBarChart` `140 Card` `70 extractRows` | `~70-90ms` | `0.2%` | `extractRows` filter `v!=="—"`, `MetricCard:273` `formatDisplayMetric`, `Recharts ResponsiveContainer` mount |
| **Total** | `main` → `ChatPage` → `Renderer` | **`14.8s – 96.0s`** | `100%` | `LLM 98%` dominates; DB+render `~0.2s` fixed |

**DB per-type `logs/db.log` median `elapsed_ms`:** `fundInfo ILIKE 28ms`, `holdings Top10 29ms`, `marketCap GROUP BY 48ms`, `aum_history 246pts 42ms`, `valuation LIMIT1 24ms`, `risk UNION 45ms`, `debt_metrics 30ms`, `funnel UNION ALL 27ms`, `plans 32ms`, `manager tenures JOIN 39ms`. No `rows:0` for valid funds after `db.py:218` fix.

---

## Last 15 Queries – One by One (deepest)

### 1. `Analyze SBI Bluechip Fund with portfolio allocation, valuation multiples and AUM history` – `2026-09-01 10:47:15` – `38.8s`
**LLM:** `38838ms` `deepseek-v4-flash` – **Complex – 7 Query()**
- Visuals: `Callout×1, Grid(3)×2 [AUM/Turnover/Risk + P/E/P/B/Yield], Grid(2) Holdings+Pie, AreaChart, RadarChart, Table Plans` – `~820 tokens`
- SQL: `Q1 overview mfi360_funds WHERE fund_name ILIKE '%SBI%' AND (ILIKE '%Bluechip%' OR '%Large Cap%') 28ms`, `Q2 holdings Top10 29ms`, `Q3 marketCap GROUP BY 48ms`, `Q4 valuation LIMIT1 24ms`, `Q5 aum_history 246pts 42ms`, `Q6 risk UNION 45ms`, `Q7 plans 32ms` – wall `48ms` parallel
- Why `38.8s`? Mid-complexity: `SKILL 1` Bluechip→Large Cap synonym + `SKILL 2+3+4+8` must generate 7 `Query()` correctly ordered `Stage1 Query → Stage2 components → Stage3 root=Column([...])` per `prompts/04_syntactic_rules.txt:2`. Prompt `51k` + 7 `Query()` → `~650 tokens` / `80tok/s` ≈ `8s` + CoT for fund resolution + Groq queue → `38s` (not cached). DB `0.1%`.

### 2. `Show Market Cap allocation and top holdings for Nippon India Small Cap Fund` – `10:49:44` – `33.4s`
**LLM:** `33457ms` – **Medium – 3 Query()**
- Visuals: `Grid(3) Fund AUM/Riskometer/Turnover, Pie MarketCap, HorizontalBar Holdings, Table` – `~380 tokens`
- SQL: `fundInfo 28ms, holdings Top10 29ms, marketCap Small71% 48ms` – wall `48ms`
- Why `33.4s`? Single-fund templated `SKILL 2` (copy-paste holdings+marketCap) – short CoT, but `Small Cap` `GROUP BY Small 71%` still needs `portfolio_date = MAX(portfolio_date)` subquery → extra tokens vs simple valuation → `33s` vs `25s` retry.

### 3. `Show Market Cap allocation and top holdings for Nippon India Small Cap Fund` (retry) – `10:50:31` – `25.8s` – **fastest single**
- Same as #2 but cached prompt + shorter generation (LLM reused `Market Cap 71%` pattern) → `25.8s` (`-7.6s`). DB cached `0.05ms` second hit.

### 4. `Compare market cap allocation and top stock holdings between HDFC Flexi Cap Fund and Parag Parikh Flexi Cap Fund` – `10:53:31` – `14.7s` (fastest overall)
**LLM:** `14785ms` – **Complex – 6 Query()** but **fast** due to templated `SKILL 2 ×2 + SKILL 6 overlap dedup`
- Visuals: `Grid(2) 2×Pie (Large/Mid/Small) + 2×Bar Top10` – `~520 tokens` but LLM copy-pastes `SKILL 2` twice → high token reuse → `14.7s` is outlier fast – no `FULL OUTER JOIN` (only `GROUP BY`), no `UNION`.
- SQL: `2×marketCap 48ms each parallel, 2×holdings 29ms each, overlap CTE MAX+GROUP BY 34ms` – wall `48ms`
- Why fastest? `deepseek-v4-flash` streaming `~120 tokens/s` when template is repeated; plus `prompts/03:106 SKILL 6` dedup `MAX()+GROUP BY` is short.

### 5. `Show valuation multiples P/E, P/B and dividend yield for SBI Large Cap Fund` – `10:57:50` – `43.9s`
**LLM:** `43931ms` – **Simple-Medium – 3 Query()**
- Visuals: `Grid(3) P/E 48.93/P/B 7.75/Yield 1.03, Bar Category & Performance Distribution, Table SBI vs Category 48.93/48.8` – `~420 tokens`
- SQL: `fundInfo 28ms, valuation LIMIT1 24ms, category avg JOIN 45ms` – wall `45ms`
- Why `43.9s`? `SKILL 8` single-row `LIMIT 1` is simple, but LLM must also generate `SBI vs Large Cap Category` table (avg across `Large Cap Fund` 40 funds) – `AVG(price_to_earnings)` → extra CoT for `GROUP BY` correctness → `43s` vs `33s` for #2.

### 6. `Show historical AUM growth trajectory for Parag Parikh Flexi Cap Fund` – `11:01:01` – `19.6s`
**LLM:** `19619ms` – **Medium – 5 Query()**
- Visuals: `AreaChart (AUM 158 pts 2014-2026 0-160k), Grid(3) AUM/Turnover/Risk, Holdings+Pie, Valuation 28.16/5.20/2.44` – `~600 tokens`
- SQL: `aum_history 42ms 158 rows, holdings 29ms, marketCap 48ms, valuation 24ms, plans 32ms` – wall `48ms`
- Why `19.6s`? `SKILL 3` `ORDER BY aum_date ASC` is single `SELECT` without `JOIN` – very short; LLM reuses `AreaChart:512` template – among fastest medium queries.

### 7. `Show risk ratios, standard deviation, beta, and Sharpe ratio for Quant Small Cap Fund` – `11:05:07` – `48.9s`
**LLM:** `48966ms` – **Medium – 4 Query()**
- Visuals: `Grid(3) StdDev 18.97/Beta 0.88/Sharpe 0.76, Radar Fund vs Category, Peer Sharpe Bar Top10, Table` – `~580 tokens`
- SQL: `risk Direct Growth 45ms, cat_avg UNION 45ms, peers Sharpe ORDER BY sharpe DESC LIMIT 10 28ms, fundInfo 28ms` – wall `45ms`
- Why `48.9s`? `SKILL 4+5` `WITH fund_risk/cat_risk UNION` is 10-line CTE – LLM must get `p.plan='Direct' AND p.option='Growth' Title Case` correct (`prompts/04:6`), plus `HorizontalBarChart` peers – extra tokens → `48s`. Previous `LEVEL_5` had `Beta/Sharpe %` bug via `src/openui-library.tsx:813` – now table correct, bar still shows `%` (charts 0.2%).

### 8. `Show debt metrics YTM, average maturity and modified duration for SBI Liquid Fund` – `11:09:39` – `56.0s`
**LLM:** `56025ms` – **Medium – 4 Query()** (expected `SKILL 9`, actual missed YTM cards on this run)
- Visuals: `Grid(3) Fund AUM/Category/Riskometer (missing YTM per screenshot), Rating Split Pie (empty → hidden after frontend fix), Holdings Bar, Table` – `~500 tokens` but debt `rating` vs `market_cap_caption` confusion adds CoT.
- SQL: `fundInfo 28ms, debt_metrics YTM 30ms (missed), rating GROUP BY 67ms (0 rows – equity template), holdings detail 47ms Top10 debt` – wall `67ms` (slowest due to `rating` scan)
- Why `56s` vs `19s` for #6? `SKILL 9` `average_maturity_unit` + `modified_duration_unit` is rarer (`mfi360_fund_debt_metrics` 1.9k rows) and LLM hesitates between `market_cap_caption` vs `rating` for pie → `56s`. After `frontend: null` hide, Rating empty Card now hidden (user requested).

### 9. `Who currently manages Parag Parikh Flexi Cap Fund? Show each active manager's tenure start date and educational qualification` – `11:11:50` – `38.3s`
**LLM:** `38319ms` – **Medium – 2 Query()**
- Visuals: `Grid(3) Fund AUM/Riskometer/Category, Table Active Fund Managers 7 rows, Bar Tenure Duration 0-16y` – `~450 tokens`
- SQL: `fundInfo 28ms, manager_tenures JOIN fund_managers WHERE t.to_date IS NULL DISTINCT 39ms (7 rows)` – wall `39ms` (was `40+` duplicates before `prompts/03:153 WHERE to_date IS NULL`)
- Why `38.3s`? `SKILL 10` `JOIN` with `DISTINCT` + `HorizontalBarChart` tenure `AGE(to_date,from_date)` – medium, but `Parag` has 7 active managers (well-known) so LLM generates quickly vs `HDFC` (no tenures) which would be slower.

### 10. `Compare Direct vs Regular plans for HDFC Flexi Cap Fund` – `11:14:51` – `73.0s`
**LLM:** `73037ms` – **Medium – 3 Query()** – **slow due to expense_ratio hide**
- Visuals: `Grid(3) Fund AUM 1,06,495 + Direct TER 0 / Regular TER 0` (now hidden via `src/openui-library.tsx:273`), `Bar Expense Ratio :0` grey, `Radar Direct vs Regular`, `Table Plans 4 rows` – `~520 tokens` but LLM generated `MetricCard TER` despite `prompts/03:151 NEVER SELECT expense_ratio` – frontend now hides `TER 0` cards (`return null`) after this build.
- SQL: `fundInfo 28ms, plans WHERE fund_id IN (HDFC) 32ms (4 rows), risk Direct vs Regular 45ms` – wall `45ms`
- Why `73s`? LLM conflict: user asks `Direct vs Regular expense` but prompt says never show `expense_ratio` (DB has `NULL` for `HDFC` `expense_ratio`) – LLM spends CoT reasoning whether to include `expense_ratio` → long `73s` + `BarChart` grey `0` confusion.

### 11. `Compare Parag Parikh Flexi Cap Fund and HDFC Flexi Cap Fund with AUM, riskometer, and fund profiles` – `11:18:20` – `78.4s`
**LLM:** `78479ms` – **Complex – 8 Query()**
- Visuals: `2×Grid(2) AUM 1,43k/1,06k + Riskometer Very High, Table Fund Profiles (empty → hidden), FundLineChart 2-series FULL OUTER JOIN 320 pts, 2×Pie, Overlap Bar, Radar, Plans, Managers 9 rows` – `~850 tokens` (largest)
- SQL: `2×aum 42ms each, 2×marketCap 48ms, overlap CTE 34ms, risk UNION 45ms, overview IN (2) 28ms (0 rows → hidden), plans 32ms, managers 39ms` – wall `48ms`
- Why `78.4s`? Most complex in set: `8 Query()` + `WITH f1/f2 CTE` for `AUM`, `WITH h1/h2 MAX+GROUP BY` for overlap (dedup), plus `fund_name ILIKE '%Parag%' AND '%Flexi Cap%'` per `prompts/03:57 AMC rule` – longest CoT; `Fund1 Aum/Fund2 Aum` legend now replaced via `prompts/03:106` to `Parag AUM/HDFC AUM`.

### 12. `Show screening funnel for Small Cap funds with AUM above 5000 Cr and low turnover` – `11:23:16` – `84.6s`
**LLM:** `84668ms` – **Medium-Complex – 3 Query()** but **second slowest**
- Visuals: `3×MetricCard 36/18/14 Funds, Funnel 36→18→14, Bar Qualifying Funds by AUM (blue), Table 14 rows` – `~480 tokens`
- SQL: `Funnel UNION ALL 3 counts 27ms, qualifying bar SELECT fund_name, aum_cr WHERE sub_nature='Small Cap' AND aum_cr>5000 32ms (10 rows), Table 14 rows 28ms` – wall `32ms`
- Why `84.6s`? `SKILL 7` `UNION ALL` formatting strict: `'1. Category Universe' not '1.CategoryUniverse'` (`prompts/03:132` – previously `1.CategoryUniverse` bug) forces LLM to be careful with quotes/spaces → slower; plus `Bar` title `Comparative Holdings Overlap vs Distribution Breakdown` hesitation → `84s` vs `14s` for #4.

### 13. `Show holdings for hdfc flexi cap fund using weight and pe` – `11:28:22` – `39.8s`
**LLM:** `39855ms` – **Simple-Medium – 3 Query()** – **synonym-healed**
- Visuals: `Grid(4) Fund AUM + P/E/P/B/Yield, Holdings Bar, Pie` – `~400 tokens`
- SQL: `fundInfo WHERE fund_name ILIKE '%HDFC%' AND '%Flexi Cap%' 28ms (106k), holdings 29ms, marketCap 48ms, valuation pe/pb 24ms` – `weight→percentage_in_net_asset, pe→price_to_earnings` healed via `db.py:60 COLUMN_ALIAS_MAP` + `AMC_SYNONYMS hdfc→HDFC` → not LLM time.
- Why `39.8s`? Lowercase `hdfc` + alias `weight/pe` adds `db.py` heal `0ms` but LLM must still include `HDFC` in `WHERE` per `prompts/03:57` – otherwise would pick `Parag` (143k) → corrected prompt adds `10s` vs simple `Nippon` `33s`.

### 14. `Analyze SBIBLUECHIP fund, Show PPFAS flexi cap fund holdings, Compare absl small cap vs nippon small cap` (batched L12) – `11:30:09` – `96.0s` (slowest)
**LLM:** `96050ms` – **Complex – 9 Query() batched**
- Visuals: 3 separate dashboards concatenated (SBI Large Cap 55k + Parag 143k + ABSL 5.7k vs Nippon 78k) – `~1100 tokens` (exceeds `GROQ_MAX_COMPLETION_TOKENS 1024` → single LLM call for 3 user queries → long)
- SQL: `SBI fundInfo 28ms, ABSL fundInfo 38ms, Nippon fundInfo 14ms, 2×marketCap 48+32ms, 2×holdings 29+42ms, aum FULL OUTER JOIN 60ms, overlap 34ms, plans 55ms, risk 18ms, valuation 15ms` – wall `60ms`
- Why `96s`? Batched `3` queries in one `User Query:` line (log shows comma-separated) → LLM must generate `3` separate `Query()` sets + `Callout` + `MetricCard` + `Pie/Bar` for each → `>900 tokens` → `deepseek-v4-flash` rate-limited `Groq 429 retry 2.5s×2` (`chains.py:78`) → `96s`. Splitting into 3 separate `Send message` clicks would be `38s+90s+90s` but batched is slower due to token limit.

### 15. `Compare Parag vs HDFC` (short alias) – `11:47:43` – `80.7s`
**LLM:** `80721ms` – **Complex – 6 Query()** same as #11 but short prompt
- Visuals: Same as #11 but user typed `Compare Parag vs HDFC` (ambiguous `vs` without `Flexi Cap`) → LLM must infer `Flexi Cap` category via `prompts/03:57` `sub_nature` + `fund_name ILIKE '%Parag%' + '%HDFC%'` → extra synonym step `ppfas`/`hdfc` → `80.7s` (similar to `78.4s`).

---

**Who takes what per query – deepest:** `LLM 14.7-96.0s` (`98%`), `DB 0.14-0.28s` (`0.7%`), `AST reorder+normalize 0.001s`, `Frontend 0.08s`. **What makes a query slow:** `Q count ×120 tokens` + `FULL OUTER JOIN/CTE` (`aun 320pts, overlap MAX+GROUP BY`) + `UNION ALL` funnel formatting + `synonym/heal` (`hdfc/ppfas/absl/bluechip`) + `NEVER expense_ratio` conflict + batched multi-query. **Fastest** (`14.7s` #4) is templated `2×Pie+2×Bar` with no `FULL OUTER`. **Slowest** (`96s` #14) is 3× dashboard batched exceeding `1024 tokens`.
