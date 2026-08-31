import React from "react";
import { createLibrary, defineComponent, reactive, useStateField, useIsStreaming } from "@openuidev/react-lang";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart as RechartsAreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Legend,
  BarChart as RechartsBarChart,
  Bar,
  RadarChart as RechartsRadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  RadialBarChart as RechartsRadialBarChart,
  RadialBar,
  FunnelChart as RechartsFunnelChart,
  Funnel,
  LabelList,
  Sankey,
} from "recharts";
import {
  Info as InfoIcon,
  AlertTriangle as AlertTriangleIcon,
  CheckCircle as CheckCircleIcon,
  AlertCircle as AlertCircleIcon,
} from "lucide-react";
import { z } from "zod/v4";

// ── Color Palette & Design Tokens ───────────────────────────────────────────

const CHART_COLORS = [
  "#2563eb", // Vibrant Blue
  "#10b981", // Emerald Green
  "#f59e0b", // Amber Yellow
  "#8b5cf6", // Purple
  "#ec4899", // Pink
  "#06b6d4", // Cyan
  "#f97316", // Orange
];

function renderAnyNode(node: any, renderNode?: (n: any) => React.ReactNode): React.ReactNode {
  if (node === null || node === undefined) return null;
  if (React.isValidElement(node)) return node;
  if (typeof node === "string" || typeof node === "number" || typeof node === "boolean") {
    return node;
  }
  if (Array.isArray(node)) {
    return node.map((item, idx) => (
      <React.Fragment key={idx}>{renderAnyNode(item, renderNode)}</React.Fragment>
    ));
  }
  if (typeof node === "object") {
    if (renderNode && typeof renderNode === "function" && (node.type === "element" || node.statementId || node.typeName)) {
      return renderNode(node);
    }
  }
  return null;
}

// Helper: "The NULL Kicker" - Strips null, undefined, NaN, and blank rows before charts
function extractRows(data: any, defaultKey?: string): Record<string, any>[] {
  if (!data) return [];
  let raw: any[] = [];
  if (Array.isArray(data)) raw = data;
  else if (typeof data === "object") {
    if (defaultKey && Array.isArray(data[defaultKey])) raw = data[defaultKey];
    else if (Array.isArray(data.plans)) raw = data.plans;
    else if (Array.isArray(data.funds)) raw = data.funds;
    else if (Array.isArray(data.peers)) raw = data.peers;
    else if (Array.isArray(data.results)) raw = data.results;
    else if (Array.isArray(data.holdings)) raw = data.holdings;
    else if (Array.isArray(data.benchmark_history)) raw = data.benchmark_history;
    else if (Array.isArray(data.composite_history)) raw = data.composite_history;
    else if (Array.isArray(data.sectors)) raw = data.sectors;
    else if (Array.isArray(data.manager_info)) raw = data.manager_info;
    else if (Array.isArray(data.allocation)) raw = data.allocation;
    else if (Array.isArray(data.history)) raw = data.history;
    else if (Array.isArray(data.data)) raw = data.data;
    else if (Array.isArray(data.rows)) raw = data.rows;
    else if (Array.isArray(data.items)) raw = data.items;
  }

  return raw.filter((row) => {
    if (!row || typeof row !== "object") return false;
    const values = Object.values(row);
    if (!values.length) return false;
    return values.some(
      (v) => v !== null && v !== undefined && v !== "" && v !== "—" && !Number.isNaN(v)
    );
  });
}

function EmptyStateBadge({ message = "No matching records found in database." }: { message?: string }) {
  return (
    <div className="p-4 bg-slate-50/70 rounded-xl border border-dashed border-slate-300 text-center my-2">
      <span className="text-xs text-slate-500 font-medium">{message}</span>
    </div>
  );
}

// ── Visual Components (shadcn/ui Enhanced) ──────────────────────────────────

function Grid(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const renderNode = fullProps?.renderNode;

  let cols = 2;
  let rawChildren = props.children;

  if (typeof props.columns === "number") {
    cols = props.columns;
  } else if (Array.isArray(props.columns) && !rawChildren) {
    rawChildren = props.columns;
    cols = 2;
  } else if (typeof props.columns === "string" && !isNaN(Number(props.columns))) {
    cols = Number(props.columns);
  }

  const colClass =
    cols === 1
      ? "grid-cols-1"
      : cols === 3
      ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
      : cols === 4
      ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"
      : "grid-cols-1 sm:grid-cols-2";

  return <div className={`grid ${colClass} gap-3 my-2.5 w-full`}>{renderAnyNode(rawChildren, renderNode)}</div>;
}

function Card(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const renderNode = fullProps?.renderNode;

  let title: string | undefined = undefined;
  let footer: string | undefined = undefined;
  let children: any = null;

  const rawValues = Object.values(props).filter((v) => v !== null && v !== undefined);

  for (const v of rawValues) {
    if (Array.isArray(v) || (typeof v === "object" && v !== null && ((v as any).type === "element" || (v as any).statementId || React.isValidElement(v)))) {
      children = v;
      break;
    }
  }

  const stringValues = rawValues.filter((v) => typeof v === "string");
  if (stringValues.length > 0) {
    title = stringValues[0] as string;
  }
  if (stringValues.length > 1) {
    footer = stringValues[1] as string;
  }

  return (
    <div className="w-full rounded-2xl border border-zinc-200/90 bg-white shadow-2xs overflow-hidden my-3 transition-all hover:border-zinc-300/90">
      {title && (
        <div className="px-4 py-3 border-b border-zinc-100 bg-zinc-50/60 flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-700">{title}</h3>
        </div>
      )}
      <div className="p-4">{renderAnyNode(children, renderNode)}</div>
      {footer && (
        <div className="border-t border-zinc-100 px-4 py-2.5 bg-zinc-50/40 text-[11px] text-zinc-500">
          {footer}
        </div>
      )}
    </div>
  );
}

const calloutStyles = {
  info: { icon: InfoIcon, bg: "bg-blue-50/70 border-blue-200/80 text-blue-950", iconColor: "text-blue-600" },
  warning: { icon: AlertTriangleIcon, bg: "bg-amber-50/70 border-amber-200/80 text-amber-950", iconColor: "text-amber-600" },
  error: { icon: AlertCircleIcon, bg: "bg-rose-50/70 border-rose-200/80 text-rose-950", iconColor: "text-rose-600" },
  success: { icon: CheckCircleIcon, bg: "bg-emerald-50/70 border-emerald-200/80 text-emerald-950", iconColor: "text-emerald-600" },
};

function Callout(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const message = props.message ?? "";
  const variant = props.variant ?? "info";
  const style = calloutStyles[variant as keyof typeof calloutStyles] || calloutStyles.info;
  const Icon = style.icon;

  return (
    <div className={`flex items-start gap-3 rounded-2xl border px-4 py-3 text-xs ${style.bg} my-2 shadow-2xs`}>
      <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${style.iconColor}`} />
      <span className="leading-relaxed font-medium">{message}</span>
    </div>
  );
}

function Tag(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const label = props.label ?? "";
  const variant = props.variant ?? "blue";
  const colors = {
    blue: "bg-blue-50 text-blue-700 border-blue-200/80",
    green: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
    amber: "bg-amber-50 text-amber-700 border-amber-200/80",
    red: "bg-rose-50 text-rose-700 border-rose-200/80",
    purple: "bg-purple-50 text-purple-700 border-purple-200/80",
  };
  const colorClass = colors[variant as keyof typeof colors] || colors.blue;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${colorClass}`}>
      {label}
    </span>
  );
}

function formatDisplayMetric(val: any): { display: string; isNumeric: boolean } {
  if (val === undefined || val === null || val === "" || val === "—") {
    return { display: "—", isNumeric: false };
  }
  if (typeof val === "number") {
    if (Object.is(val, -0) || val === 0) return { display: "0", isNumeric: true };
    if (isNaN(val)) return { display: "—", isNumeric: false };
    const formatted = Number.isInteger(val)
      ? val.toLocaleString("en-IN")
      : val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return { display: formatted, isNumeric: true };
  }
  let s = String(val).trim();
  if (s === "-0" || s === "-0.0" || s === "-0.00" || s === "₹-0" || s === "₹-0.0" || s === "₹-0.00" || s.startsWith("-0")) {
    s = s.replace(/^-0(\.0+)?/, "0");
  }
  if (s.includes("undefined") || s.includes("null") || s === "NaN" || s === "₹NaN Cr" || s === "NaN%") {
    return { display: "—", isNumeric: false };
  }
  return { display: s, isNumeric: !isNaN(Number(s.replace(/[^0-9.-]+/g, ""))) };
}

function MetricCard(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const label = props.label ?? "";
  const value = props.value;
  const subtext = props.subtext;

  const { display } = formatDisplayMetric(value);
  const isLoading = display === "—" && (value === undefined || value === null);

  return (
    <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-1.5 transition-all hover:border-zinc-300">
      <span className="text-[10px] font-bold text-zinc-500 tracking-wider uppercase">{label}</span>
      {isLoading ? (
        <div className="mt-2 flex flex-col gap-1.5 animate-pulse">
          <div className="h-6 bg-zinc-200 rounded w-28" />
          <div className="h-3 bg-zinc-100 rounded w-20" />
        </div>
      ) : (
        <>
          <div className="text-xl font-extrabold text-zinc-900 mt-1">{display}</div>
          {subtext &&
            !subtext.startsWith("0% of Net Assets") &&
            !subtext.includes("undefined") &&
            !subtext.includes("null") &&
            !subtext.includes("NaN") && (
              <span className="text-xs text-emerald-600 font-semibold mt-0.5 inline-block">{subtext}</span>
            )}
        </>
      )}
    </div>
  );
}

function FundLineChart(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rows = extractRows(props.data, "history");
  if (!rows.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 mb-3">
            Performance & Trajectory
          </h4>
          <div className="h-[180px] flex flex-col justify-center items-center gap-2 animate-pulse bg-zinc-50 rounded-xl">
            <div className="w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
            <span className="text-xs text-zinc-400">Loading live time-series…</span>
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No historical performance records found for this scheme." />;
  }

  const sample = rows[0] || {};
  const xKey = props.xKey || "date";
  const yKey = props.yKey;
  const actualX = (xKey && xKey in sample) ? xKey : Object.keys(sample).find((k) => typeof sample[k] === "string") || xKey;

  // Scan ALL rows to discover all numeric series keys (even if null in rows[0] due to inception gaps)
  const discoveredNumericKeys = new Set<string>();
  rows.forEach((r) => {
    Object.keys(r).forEach((k) => {
      if (k !== actualX && k !== "date" && k !== "portfolio_date" && k !== "fund_id" && k !== "scheme_id") {
        const val = r[k];
        if (typeof val === "number" && !isNaN(val)) {
          discoveredNumericKeys.add(k);
        }
      }
    });
  });

  let activeLines: string[] = [];
  if (Array.isArray(yKey) && yKey.length > 0) {
    activeLines = yKey;
  } else if (typeof yKey === "string" && yKey !== actualX && discoveredNumericKeys.has(yKey) && discoveredNumericKeys.size <= 1) {
    activeLines = [yKey];
  } else if (discoveredNumericKeys.size > 0) {
    activeLines = Array.from(discoveredNumericKeys);
  } else {
    activeLines = ["value"];
  }

  // Format line labels to clean Title Case
  const formatSeriesName = (key: string) => {
    return key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700">
          Performance & Trajectory Curve ({activeLines.length} Series)
        </h4>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={rows} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <XAxis dataKey={actualX} stroke="#94a3b8" fontSize={11} tickLine={false} />
          <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e4e4e7", borderRadius: 8, fontSize: 12, boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}
            formatter={(v: any, name: any) => [`₹${v} Cr`, formatSeriesName(String(name))]}
          />
          {activeLines.length > 1 && <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />}
          {activeLines.map((lineKey, idx) => (
            <Line
              key={lineKey}
              type="monotone"
              dataKey={lineKey}
              name={formatSeriesName(lineKey)}
              stroke={CHART_COLORS[idx % CHART_COLORS.length]}
              strokeWidth={2.5}
              dot={false}
              connectNulls={true}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function AreaChart(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rows = extractRows(props.data, "history");
  if (!rows.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 mb-3">
            AUM Growth Trajectory
          </h4>
          <div className="h-[180px] flex flex-col justify-center items-center gap-2 animate-pulse bg-zinc-50 rounded-xl">
            <div className="w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
            <span className="text-xs text-zinc-400">Loading timeline data…</span>
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No AUM history records found for this scheme." />;
  }

  const sample = rows[0] || {};
  const xKey = props.xKey || "date";
  const yKey = props.yKey || "aum";
  const actualX = (xKey && xKey in sample) ? xKey : Object.keys(sample).find((k) => typeof sample[k] === "string") || xKey;
  const actualY = (yKey && yKey in sample) ? yKey : Object.keys(sample).find((k) => typeof sample[k] === "number") || yKey;

  const normalizedRows = rows.map((r) => ({
    ...r,
    [actualY]: Number(r[actualY]) || 0,
  }));

  return (
    <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
      <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 mb-3">
        AUM Growth Trajectory (₹ Cr)
      </h4>
      <ResponsiveContainer width="100%" height={240}>
        <RechartsAreaChart data={normalizedRows} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <XAxis dataKey={actualX} stroke="#94a3b8" fontSize={11} tickLine={false} />
          <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e4e4e7", borderRadius: 8, fontSize: 12, boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}
            formatter={(v: any) => [`₹${v} Cr`, "AUM"]}
          />
          <Area type="monotone" dataKey={actualY} stroke="#2563eb" strokeWidth={2.5} fillOpacity={1} fill="url(#areaGradient)" connectNulls={true} />
        </RechartsAreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function PieChart(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rows = extractRows(props.data, "allocation");
  if (!rows.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 mb-3">Allocation Breakdown</h4>
          <div className="h-[180px] flex flex-col justify-center items-center gap-2 animate-pulse bg-zinc-50 rounded-xl">
            <div className="w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
            <span className="text-xs text-zinc-400">Loading allocation…</span>
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No market cap allocation data found for this scheme." />;
  }

  const sample = (rows[0] as Record<string, any>) || {};
  const nameKey = props.nameKey || "name";
  const valueKey = props.valueKey || "value";
  const actualName = (nameKey && nameKey in sample) ? nameKey : Object.keys(sample).find((k) => typeof sample[k] === "string") || nameKey;
  const actualValue = (valueKey && valueKey in sample) ? valueKey : Object.keys(sample).find((k) => typeof sample[k] === "number" || !Number.isNaN(Number(sample[k]))) || valueKey;

  const normalizedRows: Record<string, any>[] = rows.map((r: any) => ({
    ...r,
    [actualName]: String(r[actualName] ?? "Unknown"),
    [actualValue]: Number(r[actualValue]) || 0,
  }));

  const hasNegative = normalizedRows.some((r) => Number(r[actualValue]) < 0);
  if (hasNegative) {
    return <HorizontalBarChart fullProps={fullProps} />;
  }

  const positiveSlices = normalizedRows.filter((r) => Number(r[actualValue]) > 0);
  if (positiveSlices.length < 2) {
    return <DataTable fullProps={fullProps} />;
  }

  return (
    <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
      <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 mb-3">Allocation Breakdown</h4>
      <ResponsiveContainer width="100%" height={220}>
        <RechartsPieChart>
          <Pie data={positiveSlices} dataKey={actualValue} nameKey={actualName} cx="50%" cy="50%" outerRadius={70} innerRadius={35}>
            {positiveSlices.map((_, i) => (
              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v: any) => `${v}%`} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  );
}

function cleanTickLabel(str: any): string {
  if (!str) return "";
  const s = String(str);
  const cleaned = s
    .replace(/\b(Limited|Ltd\.?|Corporation|Corp\.?|Company|Co\.?)\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned.length > 24 ? cleaned.slice(0, 22) + "…" : cleaned;
}

function HorizontalBarChart(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rows = extractRows(props.data, "holdings");
  if (!rows.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 mb-3">
            Portfolio Holdings — % of Net Asset
          </h4>
          <div className="space-y-3 animate-pulse py-3">
            {[88, 68, 52, 38, 24].map((width, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <div className="h-3.5 bg-zinc-200 rounded w-28 shrink-0" />
                <div className="h-4 bg-blue-200 rounded" style={{ width: `${width}%` }} />
              </div>
            ))}
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No portfolio holdings found for this scheme." />;
  }

  const sample = rows[0] || {};
  let labelKey = props.xKey || props.yKey || "company_name";
  if (typeof sample[labelKey] === "number") {
    labelKey = Object.keys(sample).find((k) => typeof sample[k] === "string" && k !== "portfolio_date") || "company_name";
  }

  // Scan ALL rows to discover all numeric series keys
  const discoveredNumericKeys = new Set<string>();
  rows.forEach((r) => {
    Object.keys(r).forEach((k) => {
      if (k !== labelKey && k !== "portfolio_date" && k !== "fund_id" && k !== "scheme_id") {
        const val = r[k];
        if (typeof val === "number" || (!isNaN(Number(val)) && val !== null && val !== "")) {
          discoveredNumericKeys.add(k);
        }
      }
    });
  });

  const numericKeys = Array.from(discoveredNumericKeys);
  const isMultiSeries = numericKeys.length > 1;

  const normalizedRows = rows.map((r) => {
    const item: Record<string, any> = { ...r };
    numericKeys.forEach((k) => {
      item[k] = Number(r[k]) || 0;
    });
    return item;
  });

  const formatKeyName = (key: string) => {
    return key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
      <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 mb-3">
        {isMultiSeries ? "Comparative Holdings Overlap (%)" : "Distribution Breakdown"}
      </h4>
      <ResponsiveContainer width="100%" height={Math.max(260, normalizedRows.length * (isMultiSeries ? 48 : 34))}>
        <RechartsBarChart data={normalizedRows} layout="vertical" margin={{ left: 10, right: 16 }}>
          <XAxis type="number" stroke="#94a3b8" fontSize={11} unit="%" />
          <YAxis
            type="category"
            dataKey={labelKey}
            stroke="#94a3b8"
            fontSize={11}
            width={180}
            tickFormatter={cleanTickLabel}
          />
          <Tooltip
            contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e4e4e7", borderRadius: 8, fontSize: 12, boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}
            formatter={(v: any, name: any) => [`${v}%`, formatKeyName(String(name))]}
          />
          {isMultiSeries && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {isMultiSeries ? (
            numericKeys.map((k, idx) => (
              <Bar key={k} dataKey={k} name={formatKeyName(k)} fill={CHART_COLORS[idx % CHART_COLORS.length]} radius={[0, 4, 4, 0]} />
            ))
          ) : (
            <Bar dataKey={numericKeys[0] || "value"} radius={[0, 6, 6, 0]}>
              {normalizedRows.map((entry, index) => {
                const val = Number(entry[numericKeys[0] || "value"]);
                const color = val < 0 ? "#ef4444" : CHART_COLORS[index % CHART_COLORS.length];
                return <Cell key={`cell-${index}`} fill={color} />;
              })}
            </Bar>
          )}
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}

function BarChart(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rows = extractRows(props.data, "distribution");
  if (!rows.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 mb-3">
            Metric Distribution
          </h4>
          <div className="h-[180px] flex items-center justify-center animate-pulse bg-zinc-50 rounded-xl">
            <span className="text-xs text-zinc-400">Loading chart data…</span>
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No distribution records found." />;
  }

  const sample = rows[0] || {};
  let xKey = props.xKey || "name";
  let yKey = props.yKey || "value";
  const actualX = (xKey && xKey in sample) ? xKey : Object.keys(sample).find((k) => typeof sample[k] === "string") || xKey;
  const actualY = (yKey && yKey in sample) ? yKey : Object.keys(sample).find((k) => typeof sample[k] === "number" || (!isNaN(Number(sample[k])) && k !== actualX)) || yKey;

  const normalizedRows = rows.map((r) => ({
    ...r,
    [actualX]: String(r[actualX] ?? ""),
    [actualY]: Number(r[actualY]) || 0,
  }));

  const formatKeyName = (key: string) => {
    return key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="p-4 bg-white rounded-2xl border border-zinc-200/90 shadow-2xs my-2">
      <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 mb-3">
        {props.title || "Category & Performance Distribution"}
      </h4>
      <ResponsiveContainer width="100%" height={240}>
        <RechartsBarChart data={normalizedRows} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <XAxis dataKey={actualX} stroke="#94a3b8" fontSize={11} tickLine={false} tickFormatter={(v) => (String(v).length > 14 ? String(v).slice(0, 12) + "…" : String(v))} />
          <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e4e4e7", borderRadius: 8, fontSize: 12, boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}
            formatter={(v: any) => [typeof v === "number" ? `${v}` : v, formatKeyName(actualY)]}
          />
          <Bar dataKey={actualY} radius={[6, 6, 0, 0]}>
            {normalizedRows.map((entry, index) => {
              const val = Number(entry[actualY]);
              const color = val < 0 ? "#ef4444" : CHART_COLORS[index % CHART_COLORS.length];
              return <Cell key={`cell-${index}`} fill={color} />;
            })}
          </Bar>
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}



function getCellValue(row: Record<string, any>, col: string): any {
  if (row[col] !== undefined && row[col] !== null) return row[col];
  const cleanCol = col.toLowerCase().replace(/[^a-z0-9]/g, "");
  for (const [k, v] of Object.entries(row)) {
    const cleanK = k.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (cleanK === cleanCol || cleanK.includes(cleanCol) || cleanCol.includes(cleanK)) {
      return v;
    }
  }
  return "—";
}

function formatDisplayValue(val: any, col: string): string {
  if (val === null || val === undefined || val === "" || val === "—") return "—";

  const colLower = col.toLowerCase();

  // Smart Exit Load JSON parser & reader
  if (colLower.includes("exit_load") || colLower.includes("exitload")) {
    if (typeof val === "string" && (val.includes("rules") || val.includes("load_pct"))) {
      try {
        const jsonStr = val
          .replace(/'/g, '"')
          .replace(/True/g, "true")
          .replace(/False/g, "false")
          .replace(/None/g, "null");
        const parsed = JSON.parse(jsonStr);
        if (parsed.rules && Array.isArray(parsed.rules)) {
          const nonZero = parsed.rules.filter((r: any) => Number(r.load_pct) > 0);
          if (nonZero.length > 0) {
            const r = nonZero[0];
            return `${r.load_pct}% (${r.condition || `within ${r.max_holding_days || 365} days`})`;
          }
          return "Nil (0% Exit Load)";
        }
      } catch {}
    }
  }

  // Currency & Minimum Investment formatting
  if (colLower.includes("min_invest") || colLower.includes("mininvest") || colLower.includes("investment")) {
    const num = Number(val);
    if (!isNaN(num) && num > 0) {
      return `₹${num.toLocaleString("en-IN")}`;
    }
  }

  // AUM Crore formatting
  if (colLower.includes("aum_cr") || colLower.includes("aum")) {
    const num = Number(val);
    if (!isNaN(num)) {
      return `₹${num.toLocaleString("en-IN", { maximumFractionDigits: 2 })} Cr`;
    }
  }

  // Percentage / Ratio formatting
  if (typeof val === "number" && (colLower.includes("percent") || colLower.includes("ratio") || colLower.includes("expense"))) {
    return `${val}%`;
  }

  return String(val);
}

function DataTable(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rows = extractRows(props.data, "holdings");
  if (!rows.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm animate-pulse my-2">
          <div className="h-3.5 bg-slate-200 rounded w-32 mb-3" />
          <div className="space-y-2">
            <div className="h-7 bg-slate-100 rounded w-full" />
            <div className="h-7 bg-slate-100 rounded w-full" />
            <div className="h-7 bg-slate-100 rounded w-full" />
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No records found in database." />;
  }

  const columnsProp = props.columns;

  // 1. Gather all candidate columns
  interface ColDef {
    key: string;
    label: string;
  }
  let candidateCols: ColDef[] = [];

  if (Array.isArray(columnsProp) && columnsProp.length > 0) {
    candidateCols = columnsProp.map((c: any) => {
      if (typeof c === "object" && c !== null) {
        const k = c.key || c.field || c.id || Object.keys(c)[0] || "";
        const l = c.label || c.name || c.title || k;
        return { key: String(k), label: String(l) };
      }
      return { key: String(c), label: String(c) };
    });
  } else {
    // Scan all keys across rows to ensure complete coverage
    const allKeys = new Set<string>();
    rows.forEach((r: any) => {
      Object.keys(r || {}).forEach((k) => {
        if (k !== "fund_id" && k !== "scheme_id") {
          allKeys.add(k);
        }
      });
    });
    candidateCols = Array.from(allKeys).map((k) => ({ key: k, label: k }));
  }

  // 2. Layer 1 Intelligent Auto-Pruning: Discard columns that are 100% NULL / empty across all rows
  const activeCols = candidateCols.filter((col) => {
    return rows.some((row: any) => {
      const val = getCellValue(row, col.key);
      return (
        val !== null &&
        val !== undefined &&
        val !== "" &&
        val !== "—" &&
        val !== "null" &&
        val !== "None"
      );
    });
  });

  const finalCols = activeCols.length > 0 ? activeCols : candidateCols.slice(0, 6);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm my-2.5">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[10px]">
            <tr>
              {finalCols.map((col, i) => (
                <th key={i} className="px-3.5 py-2.5">
                  {col.label.replace(/_/g, " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row: any, rIdx: number) => (
              <tr key={rIdx} className="hover:bg-slate-50/70 transition-colors">
                {finalCols.map((col, cIdx) => {
                  const rawVal = getCellValue(row, col.key);
                  const displayVal = formatDisplayValue(rawVal, col.key);
                  return (
                    <td key={cIdx} className="px-3.5 py-2 text-slate-700 whitespace-nowrap">
                      {displayVal}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TextContent(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const rawText = String(props.text ?? "");
  const cleanText = rawText.replace(/^#+\s*/, "").trim();
  const isHeader = rawText.startsWith("#") || (cleanText.length < 100 && !cleanText.includes("\n"));

  return (
    <div
      className={
        isHeader
          ? "text-base font-extrabold text-slate-900 tracking-tight py-1.5"
          : "text-xs text-slate-700 leading-relaxed py-1"
      }
    >
      {cleanText}
    </div>
  );
}


function RadarChart(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rawData = extractRows(props.data, "metrics");
  const metrics = props.metrics;
  const series = props.series;

  let chartData: Record<string, any>[] = [];
  let seriesKeys: string[] = [];

  if (Array.isArray(metrics) && Array.isArray(series)) {
    const validSeries = series.filter((s: any) => typeof s?.name === "string");
    seriesKeys = validSeries.map((s: any) => s.name);
    chartData = metrics.map((metric: string, i: number) => {
      const row: Record<string, any> = { metric };
      for (const s of validSeries) {
        row[s.name] = Array.isArray(s.data) ? (s.data[i] ?? 0) : 0;
      }
      return row;
    });
  } else if (rawData.length > 0) {
    const sample = rawData[0] || {};
    const metricKeys = Object.keys(sample).filter(
      (k) => typeof sample[k] === "number" && k !== "fund_id" && k !== "scheme_id" && k !== "id"
    );
    const labelKey =
      Object.keys(sample).find(
        (k) => typeof sample[k] === "string" && !k.includes("date") && !k.includes("id")
      ) || "scheme_name";

    seriesKeys = rawData.slice(0, 4).map((r, i) => String(r[labelKey] ?? `Series ${i + 1}`));

    chartData = metricKeys.map((metricKey) => {
      const row: Record<string, any> = {
        metric: metricKey.replace(/_/g, " ").toUpperCase(),
      };
      rawData.slice(0, 4).forEach((r, idx) => {
        const sName = seriesKeys[idx];
        row[sName] = Number(r[metricKey]) || 0;
      });
      return row;
    });
  }

  if (!chartData.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm my-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">
            Risk & Volatility Radar Matrix
          </h4>
          <div className="h-[220px] flex justify-center items-center animate-pulse bg-slate-50 rounded-lg">
            <div className="w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No radar comparison metrics available." />;
  }

  return (
    <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm my-2">
      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">
        Risk & Volatility Radar Matrix
      </h4>
      <ResponsiveContainer width="100%" height={260}>
        <RechartsRadarChart data={chartData} margin={{ top: 10, right: 15, bottom: 10, left: 15 }}>
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis dataKey="metric" stroke="#64748b" fontSize={11} />
          <PolarRadiusAxis stroke="#cbd5e1" fontSize={10} />
          <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: 8, fontSize: 12 }} />
          {seriesKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />}
          {seriesKeys.map((key, idx) => (
            <Radar
              key={key}
              name={key}
              dataKey={key}
              stroke={CHART_COLORS[idx % CHART_COLORS.length]}
              fill={CHART_COLORS[idx % CHART_COLORS.length]}
              fillOpacity={0.35}
            />
          ))}
        </RechartsRadarChart>
      </ResponsiveContainer>
    </div>
  );
}


function RadialChart(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rawData = extractRows(props.data, "scores");
  const maxValue = Math.max(1, Number(props.maxValue) || 100);

  if (!rawData.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm my-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">Radial Score Gauge</h4>
          <div className="h-[220px] flex justify-center items-center animate-pulse bg-slate-50 rounded-lg">
            <div className="w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No radial score data available." />;
  }

  const sample = rawData[0] || {};
  const nameKey = props.nameKey || Object.keys(sample).find((k) => typeof sample[k] === "string") || "name";
  const valueKey = props.valueKey || Object.keys(sample).find((k) => typeof sample[k] === "number") || "value";

  const chartData = rawData.map((d, i) => ({
    name: String(d[nameKey] ?? `Item ${i + 1}`),
    value: Math.min(100, Math.max(0, ((Number(d[valueKey]) || 0) / maxValue) * 100)),
    fill: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return (
    <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm my-2">
      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">
        Radial Performance & Risk Gauge
      </h4>
      <ResponsiveContainer width="100%" height={240}>
        <RechartsRadialBarChart innerRadius="25%" outerRadius="90%" data={chartData} startAngle={180} endAngle={0}>
          <RadialBar background={{ fill: "#f1f5f9" }} dataKey="value" cornerRadius={6} />
          <Tooltip formatter={(val: any) => [`${val}%`, "Score"]} />
          <Legend iconSize={10} layout="vertical" verticalAlign="middle" align="right" wrapperStyle={{ fontSize: 11 }} />
        </RechartsRadialBarChart>
      </ResponsiveContainer>
    </div>
  );
}

function FunnelChart(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rawData = extractRows(props.data, "stages");

  if (!rawData.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm my-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">Conversion & Selection Funnel</h4>
          <div className="h-[220px] flex justify-center items-center animate-pulse bg-slate-50 rounded-lg">
            <div className="w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No funnel data available." />;
  }

  const sample = rawData[0] || {};
  const nameKey = props.nameKey || Object.keys(sample).find((k) => typeof sample[k] === "string") || "name";
  const valueKey = props.valueKey || Object.keys(sample).find((k) => typeof sample[k] === "number") || "value";

  const chartData = rawData.map((d, i) => ({
    name: String(d[nameKey] ?? `Stage ${i + 1}`),
    value: Number(d[valueKey]) || 0,
    fill: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return (
    <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm my-2">
      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">
        Fund Screening & Allocation Funnel
      </h4>
      <ResponsiveContainer width="100%" height={240}>
        <RechartsFunnelChart>
          <Tooltip formatter={(v: any) => [`${v}`, "Count / Value"]} />
          <Funnel dataKey="value" data={chartData} isAnimationActive>
            <LabelList position="right" fill="#334155" stroke="none" dataKey="name" fontSize={11} />
          </Funnel>
        </RechartsFunnelChart>
      </ResponsiveContainer>
    </div>
  );
}

function SankeyChart(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const isStreaming = useIsStreaming();
  const rawNodes = props.nodes;
  const rawLinks = props.links;
  const rawData = extractRows(props.data, "flows");

  let nodeNames: string[] = [];
  let linksList: { source: number; target: number; value: number }[] = [];

  if (Array.isArray(rawNodes) && Array.isArray(rawLinks)) {
    nodeNames = rawNodes;
    const indexMap = new Map(nodeNames.map((name, i) => [name, i]));
    linksList = rawLinks
      .map((l: any) => ({
        source: typeof l.from === "number" ? l.from : (indexMap.get(l.from ?? l.source) ?? -1),
        target: typeof l.to === "number" ? l.to : (indexMap.get(l.to ?? l.target) ?? -1),
        value: Number(l.value) || 1,
      }))
      .filter((l: any) => l.source >= 0 && l.target >= 0 && l.source !== l.target);
  } else if (rawData.length > 0) {
    const sample = rawData[0] || {};
    const fromKey = Object.keys(sample).find((k) => k.includes("from") || k.includes("source") || k.includes("sector") || k.includes("nature")) || Object.keys(sample)[0];
    const toKey = Object.keys(sample).find((k) => k.includes("to") || k.includes("target") || k.includes("company") || k.includes("name")) || Object.keys(sample)[1];
    const valKey = Object.keys(sample).find((k) => typeof sample[k] === "number") || Object.keys(sample)[2];

    const uniqueNodes = Array.from(new Set(rawData.flatMap((r) => [String(r[fromKey]), String(r[toKey])]).filter(Boolean)));
    nodeNames = uniqueNodes;
    const indexMap = new Map(nodeNames.map((name, i) => [name, i]));

    linksList = rawData
      .map((r) => ({
        source: indexMap.get(String(r[fromKey])) ?? -1,
        target: indexMap.get(String(r[toKey])) ?? -1,
        value: Number(r[valKey]) || 1,
      }))
      .filter((l) => l.source >= 0 && l.target >= 0 && l.source !== l.target);
  }

  if (!nodeNames.length || !linksList.length) {
    if (isStreaming) {
      return (
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm my-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">Capital & Allocation Flow</h4>
          <div className="h-[220px] flex justify-center items-center animate-pulse bg-slate-50 rounded-lg">
            <div className="w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          </div>
        </div>
      );
    }
    return <EmptyStateBadge message="No flow data available for Sankey diagram." />;
  }

  const data = {
    nodes: nodeNames.map((name, i) => ({
      name,
      fill: CHART_COLORS[i % CHART_COLORS.length],
    })),
    links: linksList,
  };

  return (
    <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm my-2">
      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">
        Capital & Portfolio Allocation Flow
      </h4>
      <ResponsiveContainer width="100%" height={260}>
        <Sankey
          data={data}
          nodePadding={24}
          margin={{ top: 10, left: 10, right: 10, bottom: 10 }}
          link={{ stroke: "#93c5fd", strokeOpacity: 0.6 }}
        >
          <Tooltip formatter={(v: any) => [`${v}`, "Flow Value"]} />
        </Sankey>
      </ResponsiveContainer>
    </div>
  );
}

function InputField(fullProps: any) {
  const props = fullProps?.props ?? fullProps ?? {};
  const field = useStateField(props.name, props.value);
  const isStreaming = useIsStreaming();
  return (
    <input
      name={field.name}
      placeholder={props.placeholder ?? ""}
      type={props.type ?? "text"}
      value={field.value ?? ""}
      onChange={(e) => field.setValue(e.target.value)}
      disabled={isStreaming}
      className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  );
}

// ── OpenUI Library Definitions (Single Source of Truth) ─────────────────────

const ColumnDef = defineComponent({
  name: "Column",
  description: "Vertical column layout container.",
  props: z.object({ children: z.any() }).passthrough(),
  component: (fullProps: any) => {
    const props = fullProps?.props ?? fullProps ?? {};
    return <div className="flex flex-col gap-2.5 w-full my-2">{renderAnyNode(props.children, fullProps.renderNode)}</div>;
  },
});

const RootDef = defineComponent({
  name: "Root",
  description: "Root canvas layout container.",
  props: z.object({ children: z.any() }).passthrough(),
  component: (fullProps: any) => {
    const props = fullProps?.props ?? fullProps ?? {};
    return <div className="flex flex-col gap-2.5 w-full my-2">{renderAnyNode(props.children, fullProps.renderNode)}</div>;
  },
});

const StackDef = defineComponent({
  name: "Stack",
  description: "Vertical stack layout container.",
  props: z.object({ children: z.any() }).passthrough(),
  component: (fullProps: any) => {
    const props = fullProps?.props ?? fullProps ?? {};
    return <div className="flex flex-col gap-2.5 w-full my-2">{renderAnyNode(props.children, fullProps.renderNode)}</div>;
  },
});

const ContainerDef = defineComponent({
  name: "Container",
  description: "Full-width container wrapper.",
  props: z.object({ children: z.any() }).passthrough(),
  component: (fullProps: any) => {
    const props = fullProps?.props ?? fullProps ?? {};
    return <div className="flex flex-col gap-2.5 w-full my-2">{renderAnyNode(props.children, fullProps.renderNode)}</div>;
  },
});

const RowDef = defineComponent({
  name: "Row",
  description: "Horizontal row layout container.",
  props: z.object({ children: z.any() }).passthrough(),
  component: (fullProps: any) => {
    const props = fullProps?.props ?? fullProps ?? {};
    return <div className="flex flex-col sm:flex-row gap-3 w-full my-2 items-stretch">{renderAnyNode(props.children, fullProps.renderNode)}</div>;
  },
});

const GridDef = defineComponent({
  name: "Grid",
  description: "Responsive multi-column grid layout.",
  props: z.object({
    columns: z.any().optional(),
    children: z.any().optional(),
  }).passthrough(),
  component: Grid,
});

const CardDef = defineComponent({
  name: "Card",
  description: "Elevated card wrapper with title, footer, and children.",
  props: z.object({
    title: z.any().optional(),
    footer: z.any().optional(),
    children: z.any().optional(),
  }).passthrough(),
  component: Card,
});

const CalloutDef = defineComponent({
  name: "Callout",
  description: "Informational or warning disclaimer banner.",
  props: z.object({
    message: z.any().optional(),
    variant: z.any().optional(),
  }).passthrough(),
  component: Callout,
});

const TagDef = defineComponent({
  name: "Tag",
  description: "Pill badge tag.",
  props: z.object({
    label: z.any().optional(),
    variant: z.any().optional(),
  }).passthrough(),
  component: Tag,
});

const MetricCardDef = defineComponent({
  name: "MetricCard",
  description: "Key performance indicator (KPI) metric card.",
  props: z.object({
    label: z.any().optional(),
    value: z.any().optional(),
    subtext: z.any().optional(),
  }).passthrough(),
  component: MetricCard,
});

const FundLineChartDef = defineComponent({
  name: "FundLineChart",
  description: "Time-series line chart supporting single or multi-line performance trajectories.",
  props: z.object({
    data: z.any(),
    xKey: z.any().optional(),
    yKey: z.any().optional(),
  }).passthrough(),
  component: FundLineChart,
});

const AreaChartDef = defineComponent({
  name: "AreaChart",
  description: "Gradient area chart for historical AUM wealth growth.",
  props: z.object({
    data: z.any(),
    xKey: z.any().optional(),
    yKey: z.any().optional(),
  }).passthrough(),
  component: AreaChart,
});

const PieChartDef = defineComponent({
  name: "PieChart",
  description: "Donut chart for market capitalization and asset allocation splits.",
  props: z.object({
    data: z.any(),
    nameKey: z.any().optional(),
    valueKey: z.any().optional(),
  }).passthrough(),
  component: PieChart,
});

const BarChartDef = defineComponent({
  name: "BarChart",
  description: "Vertical column bar chart for discrete categorical metrics, yearly returns, and rating distributions.",
  props: z.object({
    data: z.any(),
    xKey: z.any().optional(),
    yKey: z.any().optional(),
    title: z.any().optional(),
  }).passthrough(),
  component: BarChart,
});

const HorizontalBarChartDef = defineComponent({
  name: "HorizontalBarChart",
  description: "Horizontal bar chart for ranked holdings and multi-fund overlap comparisons.",
  props: z.object({
    data: z.any(),
    xKey: z.any().optional(),
    yKey: z.any().optional(),
  }).passthrough(),
  component: HorizontalBarChart,
});

const RadarChartDef = defineComponent({
  name: "RadarChart",
  description: "Multi-axis polar radar chart for risk metrics comparison.",
  props: z.object({
    data: z.any().optional(),
    metrics: z.any().optional(),
    series: z.any().optional(),
  }).passthrough(),
  component: RadarChart,
});

const RadialChartDef = defineComponent({
  name: "RadialChart",
  description: "Circular progress gauge meter for single metric scoring.",
  props: z.object({
    data: z.any(),
    nameKey: z.any().optional(),
    valueKey: z.any().optional(),
    maxValue: z.any().optional(),
  }).passthrough(),
  component: RadialChart,
});

const FunnelChartDef = defineComponent({
  name: "FunnelChart",
  description: "Step-by-step screening conversion funnel chart.",
  props: z.object({
    data: z.any(),
    nameKey: z.any().optional(),
    valueKey: z.any().optional(),
  }).passthrough(),
  component: FunnelChart,
});

const SankeyChartDef = defineComponent({
  name: "SankeyChart",
  description: "Flow allocation mapping chart.",
  props: z.object({
    data: z.any().optional(),
    nodes: z.any().optional(),
    links: z.any().optional(),
  }).passthrough(),
  component: SankeyChart,
});

const TableDef = defineComponent({
  name: "Table",
  description: "Data table with cell formatting.",
  props: z.object({
    data: z.any(),
    columns: z.any().optional(),
  }).passthrough(),
  component: DataTable,
});

const TextContentDef = defineComponent({
  name: "TextContent",
  description: "Typography block for headings and descriptive body text.",
  props: z.object({ text: z.any().optional() }).passthrough(),
  component: TextContent,
});

const InputFieldDef = defineComponent({
  name: "InputField",
  description: "Input form field control.",
  props: z.object({
    name: z.any().optional(),
    placeholder: z.any().optional(),
    type: z.any().optional(),
    value: z.any().optional(),
  }).passthrough(),
  component: InputField,
});


export const myLibrary = createLibrary({
  components: [
    ColumnDef,
    RootDef,
    StackDef,
    ContainerDef,
    RowDef,
    GridDef,
    CardDef,
    CalloutDef,
    TagDef,
    TextContentDef,
    MetricCardDef,
    TableDef,
    PieChartDef,
    BarChartDef,
    HorizontalBarChartDef,
    FundLineChartDef,
    AreaChartDef,
    RadarChartDef,
    RadialChartDef,
    FunnelChartDef,
    SankeyChartDef,
    InputFieldDef,
  ],
});
