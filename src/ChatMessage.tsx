import React, { useMemo, useState } from "react";
import { Renderer } from "@openuidev/react-lang";
import { myLibrary } from "./openui-library";
import { Bot, Code2, Copy, Check, Sparkles } from "lucide-react";

interface ChatMessageProps {
  text: string;
  isStreaming?: boolean;
  timestamp?: string;
  elapsedMs?: number;
}

function topologicalSortOpenUI(code: string): string {
  // 1. Group into logical statement blocks (handles multi-line statements)
  const lines = code.split("\n");
  const statements: { lhs: string; rhs: string; raw: string; deps: string[] }[] = [];

  let currentBlock: string[] = [];
  let openParens = 0;
  let openBrackets = 0;
  let openBraces = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed && openParens === 0 && openBrackets === 0 && openBraces === 0) {
      continue;
    }

    currentBlock.push(line);

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === "(") openParens++;
      else if (char === ")") openParens = Math.max(0, openParens - 1);
      else if (char === "[") openBrackets++;
      else if (char === "]") openBrackets = Math.max(0, openBrackets - 1);
      else if (char === "{") openBraces++;
      else if (char === "}") openBraces = Math.max(0, openBraces - 1);
    }

    if (openParens === 0 && openBrackets === 0 && openBraces === 0 && currentBlock.length > 0) {
      const fullStatement = currentBlock.join("\n").trim();
      currentBlock = [];

      const match = fullStatement.match(/^\s*([a-zA-Z_]\w*)\s*=\s*([\s\S]+)$/);
      if (match) {
        const lhs = match[1];
        const rhs = match[2];

        // Extract identifier dependencies from rhs
        const rawTokens = rhs.match(/\b[a-zA-Z_]\w*\b/g) || [];
        const builtins = new Set([
          "Root", "Container", "Column", "Row", "Grid", "Card", "Callout", "Tag",
          "MetricCard", "PieChart", "BarChart", "HorizontalBarChart", "FundLineChart",
          "AreaChart", "RadarChart", "RadialChart", "FunnelChart", "SankeyChart",
          "Table", "TextContent", "InputField", "Query", "sql_query", "rows", "props",
          "data", "xKey", "yKey", "nameKey", "valueKey", "title", "sql", "true", "false", "null"
        ]);

        const deps = rawTokens.filter((t) => t !== lhs && !builtins.has(t) && isNaN(Number(t)));
        statements.push({ lhs, rhs, raw: fullStatement, deps: Array.from(new Set(deps)) });
      } else {
        statements.push({ lhs: "", rhs: "", raw: fullStatement, deps: [] });
      }
    }
  }

  if (currentBlock.length > 0) {
    statements.push({ lhs: "", rhs: "", raw: currentBlock.join("\n").trim(), deps: [] });
  }

  // 2. Build Dependency Graph
  const allDefinedVars = new Set(statements.map((s) => s.lhs).filter(Boolean));
  statements.forEach((s) => {
    s.deps = s.deps.filter((d) => allDefinedVars.has(d));
  });

  // 3. Kahn's Algorithm for Topological Ordering
  const sorted: string[] = [];
  const emittedVars = new Set<string>();
  const remaining = [...statements];

  let progress = true;
  while (remaining.length > 0 && progress) {
    progress = false;
    for (let i = 0; i < remaining.length; i++) {
      const stmt = remaining[i];
      const ready = stmt.deps.every((d) => emittedVars.has(d));
      const isRoot = stmt.lhs === "root";
      const otherUnemittedNonRoot = remaining.some((r) => r !== stmt && r.lhs !== "root");

      if (ready && (!isRoot || !otherUnemittedNonRoot)) {
        sorted.push(stmt.raw);
        if (stmt.lhs) emittedVars.add(stmt.lhs);
        remaining.splice(i, 1);
        progress = true;
        break;
      }
    }
  }

  if (remaining.length > 0) {
    remaining.forEach((s) => sorted.push(s.raw));
  }

  return sorted.join("\n\n");
}

class RendererErrorBoundary extends React.Component<{ children: React.ReactNode; fallback?: React.ReactNode }, { hasError: boolean; error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }
  componentDidCatch(error: any, errorInfo: any) {
    console.warn("OpenUI Renderer caught render error:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-amber-50/60 border border-amber-200/80 rounded-2xl text-xs text-amber-900 my-2">
          <div className="font-semibold text-amber-800 mb-1">Rendering Live Stream...</div>
          <div className="text-[11px] text-amber-700/80">Resolving incoming component tree...</div>
        </div>
      );
    }
    return this.props.children;
  }
}

function rewriteMacros(code: string): string {
  // Strip null argument right after macro: @Sum(...), null -> @Sum(...)
  code = code.replace(/@(Sum|Avg|Count|Round)\(([^)]+)\)\s*,\s*null/g, '@$1($2)');

  // Handle string concatenation with macros: "₹" + @Sum(...) + " Cr"
  code = code.replace(/["'][^"']*["']\s*\+\s*@(Sum|Avg|Count|Round)\(\s*([a-zA-Z_]\w*)\.rows\.([a-zA-Z_]\w*)\s*\)\s*\+\s*["'][^"']*["']/g, '$2.rows, "$3"');
  code = code.replace(/@(Sum|Avg|Count|Round)\(\s*([a-zA-Z_]\w*)\.rows\.([a-zA-Z_]\w*)\s*\)\s*\+\s*["'][^"']*["']/g, '$2.rows, "$3"');
  code = code.replace(/["'][^"']*["']\s*\+\s*@(Sum|Avg|Count|Round)\(\s*([a-zA-Z_]\w*)\.rows\.([a-zA-Z_]\w*)\s*\)/g, '$2.rows, "$3"');
  
  // Handle nested @Round(@Sum(var.rows.col), 2)
  code = code.replace(/@Round\(\s*@(Sum|Avg|Count)\(\s*([a-zA-Z_]\w*)\.rows\.([a-zA-Z_]\w*)\s*\)\s*,\s*\d+\s*\)/g, '$2.rows, "$3"');
  
  // Handle simple @Sum(var.rows.col) / @Avg(var.rows.col)
  code = code.replace(/@(Sum|Avg|Count|Round)\(\s*([a-zA-Z_]\w*)\.rows\.([a-zA-Z_]\w*)\s*\)/g, '$2.rows, "$3"');
  
  // Handle @Sum(var.rows)
  code = code.replace(/@(Sum|Avg|Count|Round)\(\s*([a-zA-Z_]\w*)\.rows\s*\)/g, '$2.rows');
  return code;
}

function validateRenderableOpenUI(code: string, isStreaming: boolean): string {
  const loading = 'root = Column([TextContent("Generating visual insight...")])';
  const failed = 'root = Column([Callout("Unable to render this response. The generated OpenUI payload was incomplete or invalid.", "warning")])';

  if (!code.trim()) {
    return isStreaming ? loading : failed;
  }

  let parens = 0;
  let brackets = 0;
  let braces = 0;
  let inSingleQuote = false;
  let inDoubleQuote = false;
  let escaped = false;

  for (const char of code) {
    if (escaped) {
      escaped = false;
      continue;
    }
    if (char === "\\") {
      escaped = true;
      continue;
    }
    if (char === "'" && !inDoubleQuote) {
      inSingleQuote = !inSingleQuote;
      continue;
    }
    if (char === '"' && !inSingleQuote) {
      inDoubleQuote = !inDoubleQuote;
      continue;
    }
    if (inSingleQuote || inDoubleQuote) {
      continue;
    }
    if (char === "(") parens++;
    else if (char === ")") parens--;
    else if (char === "[") brackets++;
    else if (char === "]") brackets--;
    else if (char === "{") braces++;
    else if (char === "}") braces--;
    if (parens < 0 || brackets < 0 || braces < 0) {
      return isStreaming ? loading : failed;
    }
  }

  if (parens !== 0 || brackets !== 0 || braces !== 0 || inSingleQuote || inDoubleQuote) {
    return isStreaming ? loading : failed;
  }

  if (!/^\s*root\s*=/m.test(code)) {
    return isStreaming ? loading : failed;
  }

  return code;
}

export function ChatMessage({ text, isStreaming = false, timestamp, elapsedMs }: ChatMessageProps) {
  const formatElapsed = (ms?: number) => {
    if (ms === undefined || ms === null) return null;
    if (ms < 1000) return `${ms}ms`;
    const s = ms / 1000;
    if (s < 60) return `${s.toFixed(1)}s`;
    return `${(s/60).toFixed(1)}m`;
  };
  const elapsedLabel = formatElapsed(elapsedMs);
  const isCached = elapsedMs !== undefined && elapsedMs < 1000;
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sanitizedText = useMemo(() => {
    if (!text) return "";
    let code = text.trim();

    // Strip markdown fences
    code = code.replace(/^```[a-zA-Z]*\n?/gm, "").replace(/```$/gm, "").trim();

    // Normalize Root/Stack/Container → Column everywhere
    code = code.replace(/\bRoot\s*\(/g, "Column(");
    code = code.replace(/\b(Stack|Container)\s*\(/g, "Column(");

    // Collapse nested Column(Column(...)) -> Column(...) repeatedly
    let prev: string | null = null;
    while (prev !== code) {
      prev = code;
      code = code.replace(/Column\s*\(\s*Column\s*\(/g, "Column(");
    }

    // If root = Column(singleVar) or root = Column([singleVar]):
    code = code.replace(/^\s*root\s*=\s*Column\(\s*\[?\s*([a-zA-Z_]\w*)\s*\]?\s*\)\s*$/gm, "root = $1");
    code = code.replace(/^\s*root\s*=\s*Column\(\s*([a-zA-Z_]\w*)\s*\)\s*$/gm, "root = $1");

    // CRITICAL: root = varName (simple alias) → inline the variable's value
    const rootAliasMatch = code.match(/^\s*root\s*=\s*([a-zA-Z_]\w*)\s*$/m);
    if (rootAliasMatch) {
      const varName = rootAliasMatch[1];
      const varDefMatch = code.match(new RegExp(`^\\s*${varName}\\s*=\\s*(.+)$`, "m"));
      if (varDefMatch) {
        const varValue = varDefMatch[1].trim();
        code = code.replace(/^\s*root\s*=\s*[a-zA-Z_]\w*\s*$/m, `root = ${varValue}`);
      }
    }

    // Rewrite LLM macros to reactive AST component parameters
    code = rewriteMacros(code);

    // Apply Topological Sort so Queries -> Leaf Components -> Containers -> Root execute in 100% valid DAG order
    code = topologicalSortOpenUI(code);

    return validateRenderableOpenUI(code, isStreaming);
  }, [text, isStreaming]);

  const toolProvider = useMemo(
    () => ({
      async callTool(toolName: any, args: any) {
        if (typeof toolName === "object" && toolName !== null) {
          args = toolName.args ?? toolName.arguments ?? toolName.input ?? args;
          toolName = toolName.toolName ?? toolName.name ?? toolName.tool ?? String(toolName);
        }
        const base = (import.meta as any).env?.VITE_API_BASE_URL || "http://127.0.0.1:8001";
        const url =
          toolName === "sql_query"
            ? `${base}/api/tools/sql_query`
            : `${base}/api/tools/${toolName}`;
        const body =
          toolName === "sql_query"
            ? { sql: args?.sql || args?.query || "", max_rows: Math.min(200, Math.max(1, Number(args?.max_rows) || 100)) }
            : args || {};
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`Tool ${toolName} failed: ${res.status}`);
        const json = await res.json();
        return {
          content: [{ type: "text", text: JSON.stringify(json) }],
          structuredContent: json,
        };
      },
    }),
    []
  );

  const [showSource, setShowSource] = useState(false);

  return (
    <div className="group w-full bg-white border border-zinc-200/90 rounded-2xl p-5 shadow-[0_1px_4px_rgba(0,0,0,0.03)] hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)] space-y-4 transition-all">
      {/* Header Bar */}
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/25">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-zinc-900 tracking-tight">MF Saarthi Intelligence</span>
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-100/80">
                <Sparkles className="w-2.5 h-2.5" />
                Live Engine
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {timestamp && <span className="text-[11px] text-zinc-400 mr-1">{timestamp}</span>}
          {elapsedLabel && (
            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium border ${isCached ? 'bg-emerald-50 text-emerald-700 border-emerald-200/70' : 'bg-amber-50 text-amber-700 border-amber-200/70'}`} title={`Query to visual: ${elapsedLabel}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isCached ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              {isCached ? `⚡ ${elapsedLabel} cached` : `⏱ ${elapsedLabel}`}
            </span>
          )}
          <button
            onClick={handleCopy}
            className="p-1.5 text-zinc-400 hover:text-zinc-700 rounded-lg hover:bg-zinc-100 transition-colors"
            title="Copy response"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={() => setShowSource(!showSource)}
            className={`p-1.5 rounded-lg transition-colors ${
              showSource ? "bg-blue-50 text-blue-600" : "text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100"
            }`}
            title="Toggle Source Code"
          >
            <Code2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Reactive OpenUI Component Canvas */}
      <div className="w-full pt-1">
        <RendererErrorBoundary>
          <Renderer
            library={myLibrary}
            response={sanitizedText}
            isStreaming={isStreaming}
            toolProvider={toolProvider}
          />
        </RendererErrorBoundary>
      </div>

      {/* Source Code Toggle */}
      {showSource && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-zinc-200 font-mono text-[11px] leading-relaxed overflow-x-auto whitespace-pre-wrap break-words shadow-inner transition-all">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-zinc-800 text-[10px] text-zinc-500 font-sans uppercase font-bold tracking-wider">
            <span>openui-lang AST Execution Payload</span>
            <span>Declarative DSL</span>
          </div>
          <pre>{sanitizedText}</pre>
        </div>
      )}
    </div>
  );
}
