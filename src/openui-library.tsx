import { createLibrary, defineComponent, reactive, useStateField, useIsStreaming } from "@openuidev/react-lang";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Legend,
  BarChart as RechartsBarChart,
  Bar,
} from "recharts";
import { z } from "zod/v4";

// Helper to safely extract array rows from raw arrays or wrapped tool response objects
function extractRows(data: any, defaultKey?: string): Record<string, any>[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (typeof data === "object") {
    if (defaultKey && Array.isArray(data[defaultKey])) return data[defaultKey];
    if (Array.isArray(data.holdings)) return data.holdings;
    if (Array.isArray(data.data)) return data.data;
    if (Array.isArray(data.rows)) return data.rows;
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.history)) return data.history;
    if (Array.isArray(data.allocation)) return data.allocation;
  }
  return [];
}

function FundLineChart({
  data,
  xKey = "date",
  yKey = "nav",
}: {
  data: any;
  xKey?: string;
  yKey?: string;
}) {
  const rows = extractRows(data, "history");
  if (!rows.length) {
    return (
      <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm my-2">
        <h4 className="text-sm font-semibold mb-3 text-slate-700 dark:text-slate-200">
          NAV Performance History
        </h4>
        <div className="h-[180px] flex flex-col justify-center items-center gap-2 animate-pulse bg-slate-50 dark:bg-slate-800/50 rounded-lg">
          <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          <span className="text-xs text-slate-400">Loading performance data…</span>
        </div>
      </div>
    );
  }
  const sample = rows[0] || {};
  const actualX = (xKey && xKey in sample) ? xKey : Object.keys(sample).find((k) => typeof sample[k] === "string") || xKey;
  const actualY = (yKey && yKey in sample) ? yKey : Object.keys(sample).find((k) => typeof sample[k] === "number") || yKey;
  return (
    <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm my-2">
      <h4 className="text-sm font-semibold mb-3 text-slate-700 dark:text-slate-200">
        NAV Performance History
      </h4>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={rows}>
          <XAxis dataKey={actualX} stroke="#94a3b8" fontSize={12} />
          <YAxis stroke="#94a3b8" fontSize={12} />
          <Tooltip />
          <Line type="monotone" dataKey={actualY} stroke="#2563eb" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function MetricCard({
  label,
  value,
  subtext,
}: {
  label: string;
  value: any;
  subtext?: string;
}) {
  const isLoading =
    value === undefined ||
    value === null ||
    value === "" ||
    value === "—" ||
    (typeof value === "string" && (value.trim() === "" || value.includes("undefined") || value.includes("null")));

  return (
    <div className="p-4 bg-blue-50 dark:bg-slate-800 rounded-xl border border-blue-100 dark:border-slate-700 my-2">
      <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">{label}</span>
      {isLoading ? (
        <div className="mt-2 flex flex-col gap-1.5 animate-pulse">
          <div className="h-7 bg-slate-200 dark:bg-slate-700 rounded w-36" />
          <div className="h-3.5 bg-slate-200 dark:bg-slate-700 rounded w-24" />
        </div>
      ) : (
        <>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{String(value)}</div>
          {subtext &&
            !subtext.startsWith("0% of Net Assets") &&
            !subtext.startsWith("undefined") &&
            !subtext.startsWith("NaN") && (
              <span className="text-xs text-emerald-600 font-medium">{subtext}</span>
            )}
        </>
      )}
    </div>
  );
}

function TextContent({ text }: { text: string }) {
  return <div className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed">{text}</div>;
}

// -- Form components for interactive filters ($q binding) --

function InputField({
  name,
  placeholder,
  type,
  value,
}: {
  name: string;
  placeholder?: string;
  type?: string;
  value?: string;
}) {
  const field = useStateField(name, value);
  const isStreaming = useIsStreaming();
  return (
    <input
      name={field.name}
      placeholder={placeholder ?? ""}
      type={type ?? "text"}
      value={field.value ?? ""}
      onChange={(e) => field.setValue(e.target.value)}
      disabled={isStreaming}
      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  );
}

const COLORS = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

function PieChart({
  data,
  nameKey = "name",
  valueKey = "value",
}: {
  data: any;
  nameKey?: string;
  valueKey?: string;
}) {
  const rows = extractRows(data, "allocation");
  if (!rows.length) {
    return (
      <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm my-2">
        <h4 className="text-sm font-semibold mb-3 text-slate-700 dark:text-slate-200">Allocation</h4>
        <div className="h-[180px] flex flex-col justify-center items-center gap-2 animate-pulse bg-slate-50 dark:bg-slate-800/50 rounded-lg">
          <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          <span className="text-xs text-slate-400">Loading allocation…</span>
        </div>
      </div>
    );
  }
  const sample = rows[0] || {};
  const actualName = (nameKey && nameKey in sample) ? nameKey : Object.keys(sample).find((k) => typeof sample[k] === "string") || nameKey;
  const actualValue = (valueKey && valueKey in sample) ? valueKey : Object.keys(sample).find((k) => typeof sample[k] === "number") || valueKey;
  return (
    <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm my-2">
      <h4 className="text-sm font-semibold mb-3 text-slate-700 dark:text-slate-200">Allocation</h4>
      <ResponsiveContainer width="100%" height={220}>
        <RechartsPieChart>
          <Pie data={rows} dataKey={actualValue} nameKey={actualName} cx="50%" cy="50%" outerRadius={70} innerRadius={35}>
            {rows.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v: any) => `${v}%`} />
          <Legend />
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  );
}

function HorizontalBarChart({
  data,
  xKey = "percentage_in_net_asset",
  yKey = "company_name",
}: {
  data: any;
  xKey?: string;
  yKey?: string;
}) {
  const rows = extractRows(data, "holdings");
  if (!rows.length) {
    return (
      <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm my-2">
        <h4 className="text-sm font-semibold mb-3 text-slate-700 dark:text-slate-200">
          Portfolio Holdings — % of Net Asset
        </h4>
        <div className="space-y-3 animate-pulse py-3">
          {[88, 68, 52, 38, 24].map((width, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-32 shrink-0" />
              <div
                className="h-5 bg-blue-200 dark:bg-blue-900/60 rounded"
                style={{ width: `${width}%` }}
              />
            </div>
          ))}
          <div className="text-xs text-slate-400 mt-2 flex items-center gap-2">
            <div className="w-3.5 h-3.5 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
            Loading live holdings from database…
          </div>
        </div>
      </div>
    );
  }

  const sample = rows[0] || {};
  let valKey = xKey;
  let labelKey = yKey;

  // Auto-detect if xKey and yKey were supplied in reverse order
  if (typeof sample[valKey] === "string" && typeof sample[labelKey] === "number") {
    valKey = yKey;
    labelKey = xKey;
  }
  // Fallbacks if specified keys are not present in sample
  if (!(valKey in sample)) {
    valKey = Object.keys(sample).find((k) => typeof sample[k] === "number") || valKey;
  }
  if (!(labelKey in sample)) {
    labelKey = Object.keys(sample).find((k) => typeof sample[k] === "string" && k !== "portfolio_date") || labelKey;
  }

  return (
    <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm my-2">
      <h4 className="text-sm font-semibold mb-3 text-slate-700 dark:text-slate-200">
        Portfolio Holdings — % of Net Asset
      </h4>
      <ResponsiveContainer width="100%" height={Math.max(220, rows.length * 28)}>
        <RechartsBarChart data={rows} layout="vertical" margin={{ left: 40, right: 16 }}>
          <XAxis type="number" stroke="#94a3b8" fontSize={12} unit="%" />
          <YAxis type="category" dataKey={labelKey} stroke="#94a3b8" fontSize={11} width={140} />
          <Tooltip formatter={(v: any) => `${v}%`} />
          <Bar dataKey={valKey} fill="#2563eb" radius={[0, 6, 6, 0]} />
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}

function DataTable({
  data,
  columns,
}: {
  data: any;
  columns?: string[];
}) {
  const rows = extractRows(data, "holdings");
  if (!rows.length) {
    return (
      <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm animate-pulse my-2">
        <div className="h-4 bg-slate-200 rounded w-36 mb-3" />
        <div className="space-y-2">
          <div className="h-8 bg-slate-100 rounded w-full" />
          <div className="h-8 bg-slate-100 rounded w-full" />
          <div className="h-8 bg-slate-100 rounded w-full" />
        </div>
      </div>
    );
  }

  const sample = rows[0] || {};
  const activeColumns =
    columns && columns.length > 0
      ? columns
      : Object.keys(sample).filter((k) => k !== "fund_id" && k !== "scheme_id").slice(0, 5);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm my-2">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
            <tr>
              {activeColumns.map((col, i) => (
                <th key={i} className="px-4 py-3">
                  {col.replace(/_/g, " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-slate-50/70 transition-colors">
                {activeColumns.map((col, cIdx) => (
                  <td key={cIdx} className="px-4 py-2.5 whitespace-nowrap text-slate-700">
                    {typeof row[col] === "number" && col.includes("percent")
                      ? `${row[col]}%`
                      : String(row[col] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// -- Library definition (single source of truth) --

const ColumnDef = defineComponent({
  name: "Column",
  description: "Vertical flex container taking an array of children.",
  props: z.object({ children: z.array(z.any()) }),
  component: ({ props, renderNode }: any) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {renderNode(props.children)}
    </div>
  ),
});

const RowDef = defineComponent({
  name: "Row",
  description: "Horizontal flex container taking an array of children.",
  props: z.object({ children: z.array(z.any()) }),
  component: ({ props, renderNode }: any) => (
    <div style={{ display: "flex", flexDirection: "row", gap: 12, flexWrap: "wrap" }}>
      {renderNode(props.children)}
    </div>
  ),
});

const FundLineChartDef = defineComponent({
  name: "FundLineChart",
  description: "Line chart rendering NAV performance history over time.",
  props: z.object({
    data: reactive(z.any()),
    xKey: z.string().optional(),
    yKey: z.string().optional(),
  }),
  component: ({ props }: any) => <FundLineChart {...props} />,
});

const MetricCardDef = defineComponent({
  name: "MetricCard",
  description: "Card displaying a single labeled metric value with optional subtext.",
  props: z.object({
    label: z.string(),
    value: reactive(z.any()),
    subtext: reactive(z.any().optional()),
  }),
  component: ({ props }: any) => <MetricCard {...props} />,
});

const TextContentDef = defineComponent({
  name: "TextContent",
  description: "Text block for headers/titles. text: string content.",
  props: z.object({ text: reactive(z.string()) }),
  component: ({ props }: any) => <TextContent {...props} />,
});

const TableDef = defineComponent({
  name: "Table",
  description: "Data table displaying rows of financial records or peer comparisons.",
  props: z.object({
    data: reactive(z.any()),
    columns: z.array(z.string()).optional(),
  }),
  component: ({ props }: any) => <DataTable {...props} />,
});

const InputDef = defineComponent({
  name: "Input",
  description: 'Text input with binding. args: name, placeholder, type ("text"), rules, value ($binding).',
  props: z.object({
    name: z.string(),
    placeholder: z.string().optional(),
    type: z.string().optional(),
    rules: z.any().optional(),
    value: reactive(z.string().optional()),
  }),
  component: ({ props }: any) => <InputField {...props} />,
});

const FormControlDef = defineComponent({
  name: "FormControl",
  description: "Field with label and input. label: string, input: Input component.",
  props: z.object({
    label: z.string(),
    input: z.any(),
    hint: z.string().optional(),
  }),
  component: ({ props, renderNode }: any) => (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-slate-600 dark:text-slate-300">{props.label}</label>
      {renderNode(props.input)}
    </div>
  ),
});

const PieChartDef = defineComponent({
  name: "PieChart",
  description: "Pie chart for allocation/breakdown. data: array of objects or query object, nameKey: label field, valueKey: numeric field.",
  props: z.object({
    data: reactive(z.any()),
    nameKey: z.string().optional(),
    valueKey: z.string().optional(),
  }),
  component: ({ props }: any) => <PieChart {...props} />,
});

const HorizontalBarChartDef = defineComponent({
  name: "HorizontalBarChart",
  description: "Horizontal bar chart for portfolio holdings — stock vs % of net asset. data: array or query object, xKey: numeric % field, yKey: stock/company field.",
  props: z.object({
    data: reactive(z.any()),
    xKey: z.string().optional(),
    yKey: z.string().optional(),
  }),
  component: ({ props }: any) => <HorizontalBarChart {...props} />,
});

export const myLibrary = createLibrary({
  components: [
    ColumnDef,
    RowDef,
    FundLineChartDef,
    MetricCardDef,
    PieChartDef,
    HorizontalBarChartDef,
    TableDef,
    TextContentDef,
    InputDef,
    FormControlDef,
  ],
  root: "Column",
});
