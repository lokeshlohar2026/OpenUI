import React, { useMemo, useState } from "react";
import { Renderer } from "@openuidev/react-lang";
import { myLibrary } from "./openui-library";
import { Bot, Code2, Copy, Check, Sparkles } from "lucide-react";

interface ChatMessageProps {
  text: string;
  isStreaming?: boolean;
  timestamp?: string;
}

export function ChatMessage({ text, isStreaming = false, timestamp }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toolProvider = useMemo(
    () => ({
      async callTool(toolName: any, args: any) {
        const startedAt = performance.now();
        const originalToolName = toolName;
        const originalArgs = args;
        if (typeof toolName === "object" && toolName !== null) {
          args = toolName.args ?? toolName.arguments ?? toolName.input ?? args;
          toolName = toolName.toolName ?? toolName.name ?? toolName.tool ?? String(toolName);
        }
        const fallbackFundName = text.match(/(?:fundName|\\$fundName)\s*=\s*"([^"]+)"/)?.[1] ?? "";
        const rawQ = args?.q ?? args?.query ?? args?.search ?? args?.fund ?? fallbackFundName;
        const q = encodeURIComponent(rawQ);
        const limit = Number(args?.limit ?? 0);

        const fetchJson = async (url: string) => {
          const res = await fetch(url);
          const text = await res.text();
          let json: any;
          try {
            json = text ? JSON.parse(text) : null;
          } catch (error) {
            console.error("[tool-provider] parse failed", { toolName, status: res.status, text, error });
            throw error;
          }
          if (!res.ok) throw new Error(`${toolName} failed ${res.status}: ${text}`);
          return {
            content: [{ type: "text", text: JSON.stringify(json) }],
            structuredContent: json,
          };
        };

        if (toolName === "portfolio_holdings") {
          return fetchJson(`http://127.0.0.1:8000/api/tools/portfolio_holdings?q=${q}&limit=${limit}`);
        }
        if (toolName === "market_cap_allocation" || toolName === "sector_allocation") {
          return fetchJson(`http://127.0.0.1:8000/api/tools/market_cap_allocation?q=${q}`);
        }
        if (toolName === "aum_history" || toolName === "nav_history") {
          return fetchJson(`http://127.0.0.1:8000/api/tools/aum_history?q=${q}&limit=${limit || 24}`);
        }
        if (toolName === "fund_overview") {
          return fetchJson(`http://127.0.0.1:8000/api/tools/fund_overview?q=${q}`);
        }
        throw new Error(`Unknown tool: ${toolName} args=${JSON.stringify(args)}`);
      },
    }),
    [text]
  );

  return (
    <div className="w-full bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm space-y-4 transition-all">
      {/* Header Bar */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-800 tracking-tight">MF Saarthi AI</span>
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-100">
                <Sparkles className="w-2.5 h-2.5" />
                Live Postgres
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          {timestamp && <span>{timestamp}</span>}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
            title="Copy OpenUI Lang code"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? "Copied" : "Copy Code"}</span>
          </button>
        </div>
      </div>

      {/* Main Interactive OpenUI Component Tree */}
      <div className="pt-1">
        <Renderer library={myLibrary} response={text} isStreaming={isStreaming} toolProvider={toolProvider} />
      </div>

      {/* Collapsible DSL Code Viewer */}
      <details className="group rounded-xl border border-slate-200/80 bg-slate-50/80 overflow-hidden text-xs transition-all">
        <summary className="cursor-pointer px-3.5 py-2.5 font-medium text-slate-600 hover:text-slate-900 flex items-center gap-2 select-none">
          <Code2 className="w-3.5 h-3.5 text-slate-500" />
          <span>View openui-lang AST Code</span>
          <span className="ml-auto text-[10px] text-slate-400 font-mono group-open:rotate-180 transition-transform">▼</span>
        </summary>
        <div className="border-t border-slate-200/60 p-3.5 bg-slate-900 text-slate-100 font-mono text-[11px] overflow-x-auto leading-relaxed whitespace-pre-wrap break-words rounded-b-xl">
          {text}
        </div>
      </details>
    </div>
  );
}
