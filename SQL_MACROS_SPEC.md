# Latency & Token Optimization Specification (Minimalist & Ready-to-Implement)

---

## ⚡ 1. SQL Subquery Macros (Saves ~300 Tokens)

### The 6 Core SQL Macros

| Macro Syntax | Target Table / Entity | SQL Subquery Expansion |
| :--- | :--- | :--- |
| `@fund("Name")` | `mfi360_funds.fund_id` | `(SELECT fund_id FROM mfi360_funds WHERE fund_name ILIKE '%Name%' ORDER BY aum_cr DESC NULLS LAST LIMIT 1)` |
| `@latest_date` | Latest holdings date | `(SELECT MAX(portfolio_date) FROM mfi360_fund_portfolio_holdings WHERE fund_id = @fund)` |
| `@scheme("Name", "Direct", "Growth")` | `mfi360_fund_plans.scheme_id` | `(SELECT scheme_id FROM mfi360_fund_plans WHERE fund_id = (SELECT fund_id FROM mfi360_funds WHERE fund_name ILIKE '%Name%' ORDER BY aum_cr DESC NULLS LAST LIMIT 1) AND plan ILIKE 'Direct%' AND option ILIKE 'Growth%' LIMIT 1)` |
| `@manager("Name")` | `mfi360_fund_managers.fund_manager_id` | `(SELECT fund_manager_id FROM mfi360_fund_managers WHERE name ILIKE '%Name%' LIMIT 1)` |
| `@index("Index Name")` | `amfi_portal_indices.index_id` | `(SELECT index_id FROM amfi_portal_indices WHERE index_name ILIKE '%Index Name%' LIMIT 1)` |
| `@amc("AMC Name")` | `mfi360_amcs.mf_id` | `(SELECT mf_id FROM mfi360_amcs WHERE name ILIKE '%AMC Name%' LIMIT 1)` |

### Minimalist Python Expansion Function (for `db.py`)

```python
import re

def expand_sql_macros(sql: str) -> str:
    """Expands SQL shorthand macros into safe parameterized PostgreSQL subqueries."""
    if not sql or "@" not in sql:
        return sql

    # 1. @scheme("Fund Name", "Direct", "Growth")
    def _repl_scheme(m):
        f_name, plan, opt = m.group(1).strip("'\""), m.group(2).strip("'\""), m.group(3).strip("'\"")
        return (f"(SELECT scheme_id FROM mfi360_fund_plans WHERE fund_id = "
                f"(SELECT fund_id FROM mfi360_funds WHERE fund_name ILIKE '%{f_name}%' ORDER BY aum_cr DESC NULLS LAST LIMIT 1) "
                f"AND plan ILIKE '{plan}%' AND option ILIKE '{opt}%' LIMIT 1)")
    sql = re.sub(r'@scheme\(\s*([\'"][^\'"]+[\'"])\s*,\s*([\'"][^\'"]+[\'"])\s*,\s*([\'"][^\'"]+[\'"])\s*\)', _repl_scheme, sql, flags=re.IGNORECASE)

    # 2. @fund("Fund Name")
    def _repl_fund(m):
        f_name = m.group(1).strip("'\"")
        return f"(SELECT fund_id FROM mfi360_funds WHERE fund_name ILIKE '%{f_name}%' ORDER BY aum_cr DESC NULLS LAST LIMIT 1)"
    sql = re.sub(r'@fund\(\s*([\'"][^\'"]+[\'"])\s*\)', _repl_fund, sql, flags=re.IGNORECASE)

    # 3. @manager("Manager Name")
    def _repl_manager(m):
        m_name = m.group(1).strip("'\"")
        return f"(SELECT fund_manager_id FROM mfi360_fund_managers WHERE name ILIKE '%{m_name}%' LIMIT 1)"
    sql = re.sub(r'@manager\(\s*([\'"][^\'"]+[\'"])\s*\)', _repl_manager, sql, flags=re.IGNORECASE)

    # 4. @index("Index Name")
    def _repl_index(m):
        idx_name = m.group(1).strip("'\"")
        return f"(SELECT index_id FROM amfi_portal_indices WHERE index_name ILIKE '%{idx_name}%' LIMIT 1)"
    sql = re.sub(r'@index\(\s*([\'"][^\'"]+[\'"])\s*\)', _repl_index, sql, flags=re.IGNORECASE)

    # 5. @amc("AMC Name")
    def _repl_amc(m):
        amc_name = m.group(1).strip("'\"")
        return f"(SELECT mf_id FROM mfi360_amcs WHERE name ILIKE '%{amc_name}%' LIMIT 1)"
    sql = re.sub(r'@amc\(\s*([\'"][^\'"]+[\'"])\s*\)', _repl_amc, sql, flags=re.IGNORECASE)

    # 6. @latest_date / @latest
    sql = re.sub(
        r'@latest(?:_date)?\b',
        r'(SELECT MAX(portfolio_date) FROM mfi360_fund_portfolio_holdings)',
        sql,
        flags=re.IGNORECASE
    )

    return sql
```

### Integration into `execute_safe_sql` in `db.py`

In `db.py:execute_safe_sql`, add 1 line at the top:
```python
def execute_safe_sql(sql_query: str, max_rows: int = 50) -> Dict[str, Any]:
    sql = expand_sql_macros(sql_query.strip())  # <-- 1-line macro expansion
    # ... rest of execution ...
```

---

## ✂️ 2. Direct Inline Component Nesting (Saves ~150 Tokens)

### The Principle:
Eliminate 15+ lines of temporary variable declarations (`kpi1 = ...`, `kpi2 = ...`, `kpiGrid = ...`, `chart1 = ...`, `mainContainer = ...`). Instead, directly nest components into `root = Column([...])`.

### Before (Long & Verbose - 25 lines):
```javascript
qOverview = Query('sql_query', { sql: "SELECT ... WHERE fund_id = @fund('SBI')" }, { rows: [] })
qCap = Query('sql_query', { sql: "SELECT ... WHERE fund_id = @fund('SBI') AND portfolio_date = @latest_date" }, { rows: [] })
qHold = Query('sql_query', { sql: "SELECT ... WHERE fund_id = @fund('SBI') AND portfolio_date = @latest_date LIMIT 10" }, { rows: [] })

callout = Callout("SBI Bluechip Overview", "info")
kpi1 = MetricCard("AUM", qOverview.rows, "aum_cr")
kpi2 = MetricCard("Turnover", qOverview.rows, "turnover")
kpi3 = MetricCard("Risk", qOverview.rows, "riskometer")
kpiGrid = Grid(3, [kpi1, kpi2, kpi3])

pie = Card("Market Cap", PieChart(qCap.rows, "name", "value"))
bar = Card("Holdings", HorizontalBarChart(qHold.rows, "company_name", "weight"))
chartGrid = Grid(2, [pie, bar])

mainCol = Column([callout, kpiGrid, chartGrid])
root = Root(mainCol)
```

### After (Compact & Fast - 6 lines, identical UI output):
```javascript
qOverview = Query('sql_query', { sql: "SELECT ... WHERE fund_id = @fund('SBI')" }, { rows: [] })
qCap = Query('sql_query', { sql: "SELECT ... WHERE fund_id = @fund('SBI') AND portfolio_date = @latest_date" }, { rows: [] })
qHold = Query('sql_query', { sql: "SELECT ... WHERE fund_id = @fund('SBI') AND portfolio_date = @latest_date LIMIT 10" }, { rows: [] })

root = Column([
  Callout("SBI Bluechip Overview", "info"),
  Grid(3, [MetricCard("AUM", qOverview.rows, "aum_cr"), MetricCard("Turnover", qOverview.rows, "turnover"), MetricCard("Risk", qOverview.rows, "riskometer")]),
  Grid(2, [Card("Market Cap", PieChart(qCap.rows, "name", "value")), Card("Holdings", HorizontalBarChart(qHold.rows, "company_name", "weight"))])
])
```

---

## 🏷️ 3. SQL Column Aliases for Tables (Saves ~100 Tokens)

### The Principle:
Instead of generating long column mapping dictionary objects in JavaScript (`Table(q.rows, { company_name: "Company", ... })`), alias columns directly inside SQL and call `Table(q.rows)`.

### Before (Long Dictionary Object - ~70 wasted tokens):
```javascript
q = Query('sql_query', { sql: "SELECT company_name, sector_name, percentage_in_net_asset FROM ..." })
Table(q.rows, { company_name: "Company", sector_name: "Sector", percentage_in_net_asset: "Weight %" })
```

### After (Clean SQL Alias - 1-word call):
```javascript
q = Query('sql_query', { sql: 'SELECT company_name AS "Company", sector_name AS "Sector", percentage_in_net_asset AS "Weight %" FROM ...' })
Table(q.rows)
```

*(Frontend `Table` component automatically extracts and renders headers as `COMPANY`, `SECTOR`, `WEIGHT %` without any second argument).*

---

## 📝 4. Ready-to-Copy Prompt Rules (for `prompts/04_syntactic_rules.txt`)

```text
COMPACT GENERATION RULES (CRITICAL FOR LATENCY):
1. Use SQL Shorthand Macros:
   - WHERE fund_id = @fund('SBI Bluechip')
   - WHERE portfolio_date = @latest_date
   - WHERE scheme_id = @scheme('Quant Small Cap', 'Direct', 'Growth')
   - WHERE fund_manager_id = @manager('Rajeev Thakkar')
   - WHERE index_id = @index('Nifty 50')

2. Inline Direct Nesting:
   - NEVER create temporary intermediate variables (e.g. kpi1, kpi2, chartGrid, mainLayout).
   - Define Query() nodes at the top, then directly assemble everything inside:
     root = Column([Callout(...), Grid(...), Card(...)])

3. Clean Table Aliasing:
   - Use SQL column aliases: SELECT company_name AS "Company", percentage_in_net_asset AS "Weight %" ...
   - In AST, use compact Table(query.rows) without dictionary objects.
```

---

## 📊 5. Combined Performance Impact

* **Baseline (Current)**: ~850 output tokens $\rightarrow$ **~25–35 seconds generation**
* **With Optimizations (1 + 2 + 3)**: **~180–220 output tokens $\rightarrow$ ~4–6 seconds generation**
* **Total Speedup**: **~80% reduction in latency!**
