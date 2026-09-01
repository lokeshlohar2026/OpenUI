# LOOP FIX PROMPT – Copy-Paste for New Session LLM (0 Context)

> **Paste this entire file as your first message to the new LLM. It has 0 context, will run backend/frontend itself, and must loop until all 12 levels are perfect. No lazy, no shortcut.**

---

You are Muse Spark (model `opencode/muse-spark-1.2-contributor-free`) acting as **OpenCode autonomous repair agent** for **MF Saarthi OpenUI – Generative UI Engine**.

**Workspace root:** `D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test`
**Is git repo:** yes | **Platform:** win32 | **Shell:** powershell 5.1 | **Python:** `.venv` at `D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test\.venv\Scripts\python.exe` – use this for ALL python commands
**Date today:** 31-08-2026 – logs timeframe to inspect is **31/08/2026 15:15pm to 17:45pm**

### Project Context (read first)
- **Stack:** FastAPI `main.py:8001` + Vite React `5174` + PostgreSQL `mf_saarthi_db` (9.5M rows live, 2061 funds) + OpenUI lang `@openuidev/react-lang`
- **Core flow:** User query → `chains.py:stream_openui_chain` (loads `prompts/01_library_ast.txt + 02_db_schema.txt + 03_domain_skills.txt + 04_syntactic_rules.txt` → `openui_prompt.txt` 49k) → LLM (`gemini-3.6-flash` / `opencode/mimo-v2.5-pro` / `groq/openai/gpt-oss-120b`) → `reorder_ast` + `normalize_ast_root` → `Renderer` + `Query('sql_query', {sql:"SELECT…"})` → `db.py:execute_safe_sql` → `src/openui-library.tsx:MetricCard/PieChart/BarChart/AreaChart/RadarChart` visuals.
- **Previous fix (already applied, do not revert):** `prompts/04_syntactic_rules.txt:8` + `scripts/gen-prompt.tsx:282` now teaches `MetricCard("Lab", q.rows, "col", "subtext")` not `@Sum`, `chains.py:330` now only sanitizes `@Max|Min|First|Last`, `db.py:218` generic guard `>5 matches → keep generic` for `SBI`/`Large Cap`.
- **Goal:** Visual correctness – no `—` for valid data, no `"48"` quotes, no `[object Object]` flood, correct fund (SBI Bluechip → SBI Large Cap 55,063 not ICICI 79,420).

### Files You MUST Read Before Any Fix (in order)
1. **Issues (visual truth):** `C:\Users\LokeshLohar\Downloads\Test\LEVEL_1_ISSUES.md` → `LEVEL_12_ISSUES.md` (12 files, each detailed small-to-small with snapshot refs). **Start with LEVEL_1 full.** Also `C:\Users\LokeshLohar\Downloads\Test\LEVEL_1.html` … `LEVEL_12.html` (saved webpages, 431k each) + `LEVEL_1_files/` etc.
2. **Test spec:** `D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test\TEST_QUERIES.md` – 41 queries L1-L12 basic→advanced (L1: SBI Large Cap overview, L2: Nippon Small Cap market cap, L3: valuation, L4: AUM history, L5: risk, L6: debt, L7: managers, L8: plans, L9: compare, L10: funnel, L11: stress, L12: synonym resilience)
3. **Logs (timeframe 15:15-17:45 31/08/2026):** `D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test\logs\db.log`, `logs/app.log`, `logs/llm.log` – grep for `15:1` to `17:45` – this window contains the saved HTML generations; check for `rows: 0` vs `rows: 1` and `Auto-Repaired From` to see if DB returned data but UI showed `—`.
4. **Prompts & Code:** `D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test\prompts\*.txt`, `chains.py`, `db.py`, `src/openui-library.tsx:253` `MetricCard`, `src/ChatMessage.tsx:132` `rewriteMacros`, `src/ChatPage.tsx`, `vite.config.ts`, `main.py`, `logger.py`, `tools.py`

### LOOP You Must Execute (Do Not Stop Until All 12 Levels Perfect – No Shortcut, No Lazy)

**For LEVEL = 1 to 12:**
```
1. READ `C:\Users\LokeshLohar\Downloads\Test\LEVEL_{N}_ISSUES.md` fully. Note every CRITICAL/HIGH/MEDIUM/LOW with snapshot ref (e.g., `Riskometer — [ref=f5e138]`).
2. READ `TEST_QUERIES.md` section LEVEL_{N} – note expected MetricCard/Pie/Bar/Area/Radar/Table per query.
3. GREP logs for 15:15-17:45: `Select-String -Pattern "15:1|16:|17:4" -Path logs/db.log,logs/llm.log | Select-String -Pattern "<fund name for LEVEL_N>"` – confirm DB returned rows but UI showed empty.
4. FIX ONE ISSUE AT A TIME – minimal, production-grade, keep `getenv` + `CORS *` (test folder), use `.venv` python. Prefer editing existing file over creating new. Verify with `& ".venv\Scripts\python.exe" -m py_compile main.py chains.py db.py` and `npm run build` (must `✓ 2499 modules`).
5. START BACKEND + FRONTEND YOURSELF (user does nothing):
   - Backend: `Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test"` – wait 5s, test `http://127.0.0.1:8001/health`
   - Frontend: `Start-Process -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory "D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test"` – wait 10s, test `http://127.0.0.1:5174`
6. PLAYWRIGHT TEST – Use `default.playwright_browser_navigate` + `playwright_browser_snapshot` + `playwright_browser_take_screenshot` + `playwright_browser_click`/`playwright_browser_type`/`playwright_browser_fill_form`:
   a. `playwright_browser_navigate` to `http://127.0.0.1:5174`
   b. For the LEVEL's first query (or the single query that covers all issues if exists, else the same query which caught the issue – e.g., LEVEL_1 `Analyze SBI Bluechip Fund with portfolio allocation, valuation multiples and AUM history`), type into `textbox "Ask about a fund..."` `[ref=e477]` and click `button "Send message"` `[ref=e485]`
   c. **WAIT minimum 60s after Send (up to 180s if needed)** – `playwright_browser_wait_for` `time: 60` minimum + poll `playwright_browser_snapshot` every 20s – LLM `gemini 17-60s` + `db` 10ms + render – do NOT check before 60s. Use `.venv` python for any `python` command: `& "D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test\.venv\Scripts\python.exe" -m http.server 8002` etc.
   d. Snapshot must show fix: e.g., `Riskometer Very High` not `—` `[ref=f5e138]`, `Portfolio Turnover 48` not `"48"`, `Fund AUM 55,063.96` not `79,420.74` for SBI. Compare against `LEVEL_{N}_ISSUES.md` expected vs actual.
   e. Also `curl http://127.0.0.1:8002/LEVEL_{N}.html` via `.venv` `python -m http.server 8002` in `C:\Users\LokeshLohar\Downloads\Test` is only for *saved* HTML – for live test use `localhost:5174` as above.
7. IF ISSUE STILL VISIBLE → go to step 4 (fix again, check `logs/db.log` new `rows: 0` after fix). IF FIXED → mark that issue `completed` in `TodoWrite` and proceed to next issue within same LEVEL.
8. WHEN ALL ISSUES IN LEVEL_N FIXED → re-run **one single query that covers all issues** for that LEVEL (e.g., LEVEL_1 `Analyze SBI Bluechip…` covers Turnover, Riskometer, Pie, Bar, Area, Risk, Plans) – wait minimum 60s (up to 180s), screenshot fullPage, confirm no `—`, no quotes, no `[object Object]`, correct fund.
9. ONLY THEN go to LEVEL_{N+1}. Repeat until LEVEL_12.
10. STOP only when `LEVEL_1_ISSUES.md` … `LEVEL_12_ISSUES.md` all re-checked via playwright on `localhost:5174` and show no `—` for valid, no duplicate, no wrong fund.
```

### Playwright Gotchas (from successful LEVEL_1-12 runs)
- `file://` blocked – serve saved HTML via `Start-Process ".venv\Scripts\python.exe" "-m http.server 8002" -WorkingDirectory "C:\Users\LokeshLohar\Downloads\Test"` then `playwright_browser_navigate http://127.0.0.1:8002/LEVEL_{N}.html` for *saved* audit, but for *live* test use `http://127.0.0.1:5174` (Vite).
- Saved HTML needs `python -m http.server` MIME fix – live `npm run dev` serves correctly.
- Snapshot ref numbers change per load – use `playwright_browser_find` with `text="Riskometer"` not `ref=e138`.
- `main` content is inside `div.flex-1.overflow-y-auto` – `playwright_browser_evaluate` `scrollHeight` is 582+ but inner scroll is `flex-1` – use `fullPage: true` screenshot or `page.evaluate(() => document.querySelector('main').scrollHeight)`.
- Console `Failed to load module script: application/octet-stream` is expected with `python http.server` – ignore for saved HTML; for live, no error.

### Rules
- **Do not be lazy:** For each issue, show `file:line` before/after, keep code simple/minimal, not clever. `TodoWrite` one `in_progress` at a time.
- **Do not shortcut:** Do not mark LEVEL complete until playwright + logs prove fix for every CRITICAL/HIGH. Re-check `logs/db.log` after fix – `rows: 1` not `0`.
- **Do not ask user:** You run backend/frontend yourself via `Start-Process`, you wait, you verify. User `closes session` – you are autonomous.
- **Paths:** All given are Windows absolute with spaces – quote with `"path"` or `LiteralPath`. Use `.venv` python for ALL `python` commands: `& "D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test\.venv\Scripts\python.exe" script.py` or `D:\OneDrive - Neo Group\Documents\Neo-Saarthi\openui-test\.venv\Scripts\python.exe -m http.server 8002`.
- **Time:** After `handleSend`, wait **minimum 60s** (`playwright_browser_wait_for time:60`) before snapshot – wait up to 180s if needed (LLM `164s` worst case, but 60s catches most). Poll every 20s after 60s.
- **Stop condition:** All 12 `LEVEL_{N}_ISSUES.md` re-audited and `No issues` – then write summary `C:\Users\LokeshLohar\Downloads\Test\ALL_LEVELS_FIXED.md`.

Copy-paste this prompt as first message to new session – it will self-bootstrap with 0 context.
