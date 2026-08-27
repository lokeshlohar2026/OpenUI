# 📘 Developer Blueprint: Database Tool Integration for OpenUI / Morphic

This guide explains how to add and replicate **live database function tools** connecting PostgreSQL to OpenUI / Morphic generative interfaces.

---

## 🏗️ 1. High-Level Architecture

```text
User Question
    ⬇️
Groq/Gemini LLM
    ⬇️  (Emits: data = Query("tool_name", {q: "FundName"}, {"holdings": []}))
OpenUI AST Parser (Browser)
    ⬇️  (Calls toolProvider in ChatMessage.tsx)
FastAPI Backend (:8000)
    ⬇️  (Executes parameterized SQL over PostgreSQL: 9.5M rows)
Live Records JSON Response
    ⬇️  (Unwrapped by extractRows in openui-library.tsx)
Interactive Recharts / MetricCards Rendered 🎉
```

---

## 🛠️ Step 1: Create the SQL Endpoint in FastAPI (`main.py`)

Write an optimized, parameterized endpoint querying PostgreSQL.

```python
# In main.py

@app.get("/api/tools/portfolio_holdings")
def portfolio_holdings(q: str = "", limit: int = 0):
    """Returns top stock holdings sorted by % net asset."""
    if not q.strip():
        return {"holdings": []}
    try:
        conn = pg_conn()
        cur = conn.cursor()
        
        # 1. Fuzzy match fund_id from name
        fund_id, fund_name = find_fund(cur, q)
        if not fund_id:
            conn.close()
            return {"holdings": [], "fund_name": None}

        # 2. Get latest portfolio date
        cur.execute("SELECT MAX(portfolio_date) FROM mfi360_fund_portfolio_holdings WHERE fund_id=%s", (fund_id,))
        max_date = cur.fetchone()[0]

        # 3. Query records
        query = """
            SELECT company_name, percentage_in_net_asset, portfolio_date
            FROM mfi360_fund_portfolio_holdings
            WHERE fund_id=%s AND portfolio_date=%s
            ORDER BY percentage_in_net_asset DESC
        """
        if limit and limit > 0:
            query += f" LIMIT {limit}"

        cur.execute(query, (fund_id, max_date))
        holdings = [
            {
                "company_name": r[0],
                "percentage_in_net_asset": round(float(r[1]), 2) if r[1] is not None else 0,
                "portfolio_date": r[2].isoformat(),
            }
            for r in cur.fetchall()
        ]
        conn.close()
        return {"holdings": holdings, "fund_name": fund_name, "fund_id": fund_id}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
```

---

## 🔌 Step 2: Wire Tool Provider in Frontend (`src/ChatMessage.tsx`)

OpenUI triggers `toolProvider.callTool(toolName, args)` in the browser whenever a `Query("tool_name", ...)` node is parsed.

```tsx
// In src/ChatMessage.tsx

const toolProvider = useMemo(
  () => ({
    async callTool(toolName: any, args: any) {
      if (typeof toolName === "object" && toolName !== null) {
        args = toolName.args ?? toolName.input ?? args;
        toolName = toolName.toolName ?? toolName.name ?? String(toolName);
      }
      
      const q = encodeURIComponent(args?.q ?? args?.query ?? "");
      const limit = Number(args?.limit ?? 0);

      const fetchJson = async (url: string) => {
        const res = await fetch(url);
        const json = await res.json();
        if (!res.ok) throw new Error(`${toolName} failed ${res.status}`);
        return {
          content: [{ type: "text", text: JSON.stringify(json) }],
          structuredContent: json, // 👈 Required for OpenUI reactive state
        };
      };

      if (toolName === "portfolio_holdings") {
        return fetchJson(`http://127.0.0.1:8000/api/tools/portfolio_holdings?q=${q}&limit=${limit}`);
      }
      
      throw new Error(`Unknown tool: ${toolName}`);
    },
  }),
  []
);
```

---

## 📝 Step 3: Define Tool Schema & Compile Prompt (`scripts/gen-prompt.tsx`)

Define the tool's JSON schema so `myLibrary.prompt()` can teach the LLM the exact function signature and output structure.

```typescript
// In scripts/gen-prompt.tsx

const portfolioHoldingsTool: ToolDefinition = {
  name: "portfolio_holdings",
  description:
    "Get portfolio holdings (stock and % of net asset) for any fund/AMC. Returns { holdings: [{ company_name: string, percentage_in_net_asset: number }] }. Use HorizontalBarChart(data.holdings, 'percentage_in_net_asset', 'company_name'). Always use empty default: Query('portfolio_holdings', {q: '...'}, {holdings: []})",
  inputSchema: {
    type: "object",
    properties: {
      q: { type: "string", description: "Fund/AMC name substring" },
      limit: { type: "number", description: "Max holdings rows (default 0 = all)" },
    },
    required: ["q"],
  },
  outputSchema: {
    type: "object",
    properties: {
      holdings: {
        type: "array",
        items: {
          type: "object",
          properties: {
            company_name: { type: "string" },
            percentage_in_net_asset: { type: "number" },
          },
        },
      },
    },
  },
};

// Pass to prompt compiler
let prompt = mod.myLibrary.prompt({
  tools: [portfolioHoldingsTool],
});

// Append strict Zero-Mock-Data Guardrails
prompt += `
## CRITICAL PREDEFINED SQL DATA RULES
1. NEVER insert fake or mock numbers in Query() default arguments.
2. ALWAYS use empty defaults: \`data = Query("portfolio_holdings", {q: "FundName"}, {"holdings": []})\`.
3. In Query args, use exact string literals for \`q: "FundName"\`.
`;

writeFileSync("openui_prompt.txt", prompt, "utf-8");
```

Compile with:
```bash
npm run gen:prompt
```

---

## 🎨 Step 4: React Component Defensive Data Extraction (`src/openui-library.tsx`)

Because the tool returns an object wrapper `{"holdings": [...]}` rather than a flat array, write an `extractRows` helper to handle both safely:

```tsx
// In src/openui-library.tsx

function extractRows(data: any, defaultKey?: string): Record<string, any>[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (typeof data === "object") {
    if (defaultKey && Array.isArray(data[defaultKey])) return data[defaultKey];
    if (Array.isArray(data.holdings)) return data.holdings;
    if (Array.isArray(data.allocation)) return data.allocation;
    if (Array.isArray(data.history)) return data.history;
  }
  return [];
}

function HorizontalBarChart({ data, xKey = "percentage_in_net_asset", yKey = "company_name" }: any) {
  const rows = extractRows(data, "holdings");

  // Show animated pulse skeleton while waiting for DB response
  if (!rows.length) {
    return (
      <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border animate-pulse">
        <div className="text-xs text-slate-400">Loading live holdings from database…</div>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(220, rows.length * 28)}>
      <RechartsBarChart data={rows} layout="vertical">
        <XAxis type="number" unit="%" />
        <YAxis type="category" dataKey={yKey} width={140} />
        <Tooltip formatter={(v: any) => `${v}%`} />
        <Bar dataKey={xKey} fill="#2563eb" />
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
```

---

## 🔄 Replication Summary Checklist

To add any new database tool in the future:

1. [ ] **FastAPI (`main.py`)**: Add `@app.get("/api/tools/<tool_name>")` with parameterized SQL.
2. [ ] **Frontend (`ChatMessage.tsx`)**: Add `if (toolName === "<tool_name>") return fetchJson(...)`.
3. [ ] **Prompt Generator (`gen-prompt.tsx`)**: Add `ToolDefinition` with JSON schema $\rightarrow$ run `npm run gen:prompt`.
4. [ ] **UI Component (`openui-library.tsx`)**: Use `extractRows(data, "<key>")` with loading skeleton.
