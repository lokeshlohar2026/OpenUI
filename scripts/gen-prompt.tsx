import { createServer } from "vite";
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
  outputSchema: {
    type: string;
    properties: Record<string, any>;
  };
}

const root = dirname(dirname(fileURLToPath(import.meta.url)));

const vite = await createServer({
  root,
  server: { middlewareMode: true },
  appType: "custom",
  logLevel: "error",
});

const portfolioHoldingsTool: ToolDefinition = {
  name: "portfolio_holdings",
  description:
    "Get portfolio holdings (stock and % of net asset) for any fund/AMC. Returns { holdings: [{ company_name: string, percentage_in_net_asset: number }] }. Use HorizontalBarChart(data.holdings, 'percentage_in_net_asset', 'company_name'). Always use empty default: Query('portfolio_holdings', {q: '...'}, {holdings: []})",
  inputSchema: {
    type: "object",
    properties: {
      q: { type: "string", description: "Fund/AMC name substring, e.g. 'HDFC Flexi Cap', 'SBI Bluechip'" },
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
            portfolio_date: { type: "string" },
          },
        },
      },
    },
  },
};

const marketCapAllocationTool: ToolDefinition = {
  name: "market_cap_allocation",
  description:
    "Get Market Cap allocation (Large Cap, Mid Cap, Small Cap % of portfolio). Returns { allocation: [{ name: string, value: number }] }. Use PieChart(data.allocation, 'name', 'value'). Always use empty default: Query('market_cap_allocation', {q: '...'}, {allocation: []})",
  inputSchema: {
    type: "object",
    properties: {
      q: { type: "string", description: "Fund/AMC name substring" },
    },
    required: ["q"],
  },
  outputSchema: {
    type: "object",
    properties: {
      allocation: {
        type: "array",
        items: {
          type: "object",
          properties: {
            name: { type: "string" },
            value: { type: "number" },
          },
        },
      },
    },
  },
};

const aumHistoryTool: ToolDefinition = {
  name: "aum_history",
  description:
    "Get monthly AUM history (in ₹ Cr) over time for growth charts. Returns { history: [{ date: string, aum: number }] }. Use FundLineChart(data.history, 'date', 'aum'). Always use empty default: Query('aum_history', {q: '...'}, {history: []})",
  inputSchema: {
    type: "object",
    properties: {
      q: { type: "string", description: "Fund/AMC name substring" },
      limit: { type: "number", description: "Number of months (default 24)" },
    },
    required: ["q"],
  },
  outputSchema: {
    type: "object",
    properties: {
      history: {
        type: "array",
        items: {
          type: "object",
          properties: {
            date: { type: "string" },
            aum: { type: "number" },
          },
        },
      },
    },
  },
};

const fundOverviewTool: ToolDefinition = {
  name: "fund_overview",
  description:
    "Get fund meta information (AUM, Category, Riskometer, Fund Managers). Returns { overview: { fund_name: string, aum_cr: string, nature: string, sub_nature: string, riskometer: string, managers: string } }. Always use empty default: Query('fund_overview', {q: '...'}, {overview: {}})",
  inputSchema: {
    type: "object",
    properties: {
      q: { type: "string", description: "Fund/AMC name substring" },
    },
    required: ["q"],
  },
  outputSchema: {
    type: "object",
    properties: {
      overview: {
        type: "object",
        properties: {
          fund_name: { type: "string" },
          aum_cr: { type: "string" },
          nature: { type: "string" },
          sub_nature: { type: "string" },
          riskometer: { type: "string" },
          managers: { type: "string" },
        },
      },
    },
  },
};

try {
  const mod = await vite.ssrLoadModule("/src/openui-library.tsx");
  let prompt: string = mod.myLibrary.prompt({
    tools: [portfolioHoldingsTool, marketCapAllocationTool, aumHistoryTool, fundOverviewTool],
  });

  const strictAccuracyRules = `
## CRITICAL PREDEFINED SQL DATA RULES (100% DATABASE DRIVEN, ZERO HARDCODED DATA)
1. NEVER hardcode static arrays or mock metric values (NEVER write \`marketCapData = [...]\`, \`aumGrowthData = [...]\`, or hardcoded numbers).
2. ALWAYS use the predefined SQL tools via Query() for ALL charts and metrics:
   - For Portfolio Holdings: \`holdingsData = Query("portfolio_holdings", {q: "FundName", limit: 0}, {"holdings": []})\`
   - For Market Cap Allocation: \`allocData = Query("market_cap_allocation", {q: "FundName"}, {"allocation": []})\`
   - For AUM Growth History: \`aumData = Query("aum_history", {q: "FundName"}, {"history": []})\`
   - For Fund Overview Metrics: \`metaData = Query("fund_overview", {q: "FundName"}, {"overview": {}})\`
3. In \`portfolio_holdings\`, set \`limit: 0\` to fetch ALL holdings from PostgreSQL (e.g. 70+ rows).
4. ALWAYS declare all Query() statements near the top (right after root) so the runtime resolves them immediately.
5. In every Query() args object, use the exact fund name as a string literal. Do NOT use a variable reference like \`fundName\` or \`$fundName\` for \`q\`; the renderer may pass it as null/empty.
6. In chart components:
   - \`PieChart(allocData.allocation, "name", "value")\`
   - \`FundLineChart(aumData.history, "date", "aum")\`
   - \`HorizontalBarChart(holdingsData.holdings, "percentage_in_net_asset", "company_name")\`
`;

  prompt = prompt + "\n" + strictAccuracyRules;
  writeFileSync(join(root, "openui_prompt.txt"), prompt, "utf-8");
  console.log("openui_prompt.txt written:", prompt.length, "chars (portfolio_holdings tool)");
} finally {
  await vite.close();
}
