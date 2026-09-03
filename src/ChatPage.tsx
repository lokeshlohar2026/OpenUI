import React, { useState, useRef, useEffect } from "react";
import { ChatMessage } from "./ChatMessage";
import {
  Sparkles,
  Bot,
  Plus,
  Trash2,
  PieChart,
  ShieldCheck,
  Database,
  Zap,
  Layers,
  Scale,
  Users,
  ArrowUp,
  User,
} from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  elapsedMs?: number;
}

const SUGGESTIONS = [
  {
    icon: Scale,
    label: "Compare two funds",
    detail: "PPFAS vs HDFC Flexi Cap",
    prompt:
      "Compare Parag Parikh Flexi Cap Fund and HDFC Flexi Cap Fund using the latest portfolio data and holdings.",
  },
  {
    icon: ShieldCheck,
    label: "Review risk metrics",
    detail: "Sharpe, Beta & Std Dev",
    prompt:
      "Show risk ratios, standard deviation, beta, and Sharpe ratio for Quant Small Cap Fund.",
  },
  {
    icon: PieChart,
    label: "Explore allocation",
    detail: "Market-cap composition",
    prompt:
      "Show Market Cap allocation and top holdings for Nippon India Small Cap Fund.",
  },
  {
    icon: Users,
    label: "Check fund managers",
    detail: "Active team & tenure",
    prompt:
      "Who currently manages Parag Parikh Flexi Cap Fund? Show each active manager's tenure start date and educational qualification.",
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [input, setInput] = useState("");
  const [currentStream, setCurrentStream] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStream]);

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText ?? input).trim();
    if (!textToSend || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setLoading(true);
    setCurrentStream("");

    const assistantMsgId = crypto.randomUUID();
    const assistantTimestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const queryStartTime = performance.now();

    try {
      const base = (import.meta as any).env?.VITE_API_BASE_URL || "http://127.0.0.1:8001";
      const response = await fetch(`${base}/api/v1/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: textToSend, session_id: sessionId }),
      });

      if (!response.ok) throw new Error(`Server returned ${response.status}`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      let accumulated = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulated += chunk;
        setCurrentStream(accumulated);
      }

      const elapsedMs = Math.round(performance.now() - queryStartTime);
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: "assistant",
          content: accumulated,
          timestamp: assistantTimestamp,
          elapsedMs,
        },
      ]);
      setCurrentStream("");
    } catch (err) {
      console.error("Streaming error:", err);
      const elapsedMs = Math.round(performance.now() - queryStartTime);
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: "assistant",
          content: `root = Column([TextContent("Error: Unable to load fund data from backend. Please verify FastAPI is running at :8001")])`,
          timestamp: assistantTimestamp,
          elapsedMs,
        },
      ]);
    } finally {
      setLoading(false);
      setCurrentStream("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setSessionId(crypto.randomUUID());
    setMessages([]);
    setCurrentStream("");
    setInput("");
  };

  return (
    <div className="flex h-screen w-full bg-[#fbfbfd] font-sans text-zinc-900 overflow-hidden antialiased">
      {/* ── Left Sidebar ──────────────────────────────────────────────── */}
      <aside
        className={`${
          isSidebarOpen ? "w-72" : "w-0 -translate-x-full"
        } transition-all duration-300 ease-in-out border-r border-zinc-200/80 bg-white flex flex-col shrink-0 z-20 overflow-hidden`}
      >
        {/* Sidebar Header / Brand */}
        <div className="p-4 border-b border-zinc-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-zinc-900 tracking-tight">MF Saarthi</h1>
              <span className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider">
                Generative UI Engine
              </span>
            </div>
          </div>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-zinc-50 hover:bg-zinc-100 text-zinc-800 text-xs font-semibold border border-zinc-200/80 transition-colors shadow-2xs"
          >
            <Plus className="w-4 h-4 text-zinc-600" />
            <span>New Research</span>
          </button>
        </div>

        {/* Quick Starters in Sidebar */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
          <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
            Suggested Analysis
          </div>
          {SUGGESTIONS.map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={idx}
                onClick={() => handleSend(item.prompt)}
                disabled={loading}
                className="w-full text-left p-2.5 rounded-xl hover:bg-zinc-50 text-xs transition-colors flex items-start gap-2.5 group border border-transparent hover:border-zinc-200/80"
              >
                <div className="p-1.5 rounded-lg bg-zinc-100 group-hover:bg-blue-50 group-hover:text-blue-600 text-zinc-500 transition-colors">
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-zinc-800 truncate">{item.label}</div>
                  <div className="text-[11px] text-zinc-400 truncate">{item.detail}</div>
                </div>
              </button>
            );
          })}
        </div>

        {/* System Status Footer */}
        <div className="p-3.5 border-t border-zinc-100 bg-zinc-50/50 space-y-2">
          <div className="flex items-center justify-between text-[11px] text-zinc-600">
            <span className="flex items-center gap-1.5 font-medium">
              <Database className="w-3.5 h-3.5 text-emerald-600" />
              Postgres DB
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold text-[10px] border border-emerald-200/70">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              9.5M rows live
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-zinc-600">
            <span className="flex items-center gap-1.5 font-medium">
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              Groq Engine
            </span>
            <span className="text-[10px] font-mono text-zinc-500 bg-zinc-200/70 px-1.5 py-0.5 rounded">
              gpt-oss-20b
            </span>
          </div>
        </div>
      </aside>

      {/* ── Main Chat Area ────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col h-full bg-[#fbfbfd] relative min-w-0">
        {/* Top Navbar */}
        <header className="h-14 border-b border-zinc-200/80 bg-white/80 backdrop-blur-md px-5 flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-500 hover:text-zinc-800 transition-colors"
              title="Toggle sidebar"
            >
              <Layers className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-zinc-900">Mutual Fund Intelligence</span>
              <span className="text-[11px] font-medium text-zinc-400 hidden sm:inline-block">
                • OpenUI Reactive Interface
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={handleNewChat}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-600 hover:text-rose-600 hover:bg-rose-50 rounded-lg border border-zinc-200/80 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </header>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Morphic UI Empty State Welcome Hero */}
            {messages.length === 0 && !currentStream && (
              <div className="flex-1 flex flex-col items-center justify-center gap-8 text-center px-4 py-12">
                {/* Logo mark */}
                <div className="flex flex-col items-center gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-blue-600/10 border border-blue-600/20 flex items-center justify-center text-blue-600 shadow-sm">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-zinc-900 tracking-tight">
                      What would you like to research?
                    </h2>
                    <p className="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">
                      Ask about funds, portfolios, managers, holdings, risk, or comparisons.
                    </p>
                  </div>
                </div>

                {/* Morphic Suggestion Chips */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-xl text-left">
                  {SUGGESTIONS.map(({ icon: Icon, label, detail, prompt }) => (
                    <button
                      key={label}
                      onClick={() => handleSend(prompt)}
                      className="group flex items-start gap-3.5 rounded-2xl border border-zinc-200/90 bg-white px-4 py-3.5 text-left transition-all hover:border-blue-500/40 hover:bg-blue-50/20 shadow-2xs hover:shadow-xs"
                    >
                      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400 transition-colors group-hover:text-blue-600" />
                      <span className="min-w-0">
                        <span className="block text-xs font-semibold text-zinc-800 group-hover:text-zinc-900">
                          {label}
                        </span>
                        <span className="mt-0.5 block text-[11px] leading-4 text-zinc-400">
                          {detail}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Conversation Messages */}
            {messages.map((msg) => (
              <div key={msg.id} className="space-y-2">
                {msg.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="max-w-2xl bg-zinc-900 text-white rounded-2xl rounded-tr-xs px-4 py-2.5 shadow-sm flex items-start gap-2.5">
                      <div className="text-xs leading-relaxed font-normal">{msg.content}</div>
                      <div className="w-5 h-5 rounded-full bg-zinc-700 flex items-center justify-center shrink-0 mt-0.5">
                        <User className="w-3 h-3 text-zinc-200" />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="w-full">
                    <ChatMessage text={msg.content} timestamp={msg.timestamp} elapsedMs={msg.elapsedMs} />
                  </div>
                )}
              </div>
            ))}

            {/* Live Streaming Message */}
            {currentStream && (
              <div className="w-full">
                <ChatMessage text={currentStream} isStreaming={true} timestamp="Generating..." />
              </div>
            )}

            {loading && !currentStream && (
              <div className="w-full bg-white border border-zinc-200/80 rounded-2xl p-6 shadow-sm flex items-center gap-3 animate-pulse">
                <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center text-white">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="space-y-1.5 flex-1">
                  <div className="h-3 bg-zinc-200 rounded w-48" />
                  <div className="h-2.5 bg-zinc-100 rounded w-32" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* ── Morphic UI Floating Input Bar ──────────────────────────── */}
        <div className="px-4 pb-5 pt-2 bg-gradient-to-t from-[#fbfbfd] via-[#fbfbfd]/95 to-transparent shrink-0">
          <div className="mx-auto max-w-4xl">
            {/* Quick Suggestion Pills */}
            {messages.length > 0 && !loading && (
              <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none text-[11px]">
                <span className="text-zinc-400 shrink-0 font-medium">Try:</span>
                <button
                  onClick={() => handleSend("Show top holdings for SBI Small Cap Fund")}
                  className="px-2.5 py-1 rounded-full bg-white border border-zinc-200/80 hover:border-blue-300 hover:text-blue-600 text-zinc-600 shrink-0 transition-colors shadow-2xs"
                >
                  SBI Small Cap Holdings
                </button>
                <button
                  onClick={() => handleSend("Show Market Cap allocation for Quant Active Fund")}
                  className="px-2.5 py-1 rounded-full bg-white border border-zinc-200/80 hover:border-blue-300 hover:text-blue-600 text-zinc-600 shrink-0 transition-colors shadow-2xs"
                >
                  Quant Active Allocation
                </button>
                <button
                  onClick={() => handleSend("Compare HDFC Flexi Cap vs Parag Parikh Flexi Cap Fund")}
                  className="px-2.5 py-1 rounded-full bg-white border border-zinc-200/80 hover:border-blue-300 hover:text-blue-600 text-zinc-600 shrink-0 transition-colors shadow-2xs"
                >
                  Flexi Cap Comparison
                </button>
              </div>
            )}

            {/* Morphic Rounded-2xl Input Container */}
            <div className="relative rounded-2xl bg-white border border-zinc-200 shadow-md focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all duration-150">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="Ask about a fund, manager, holding, or risk metric..."
                disabled={loading}
                className="w-full resize-none bg-transparent px-4 pt-3.5 pb-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:outline-none disabled:opacity-40 leading-relaxed font-normal"
              />

              {/* Bottom bar inside input */}
              <div className="flex items-center justify-between px-3 pb-2.5 pt-1 border-t border-zinc-100">
                <div className="flex items-center gap-1.5 text-[11px] font-medium text-blue-600 bg-blue-50/80 px-2 py-0.5 rounded-md border border-blue-100/60">
                  <Sparkles className="h-3 w-3" />
                  <span>UI Mode</span>
                </div>

                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim() || loading}
                  className="flex h-7 w-7 items-center justify-center rounded-lg bg-zinc-900 text-white shadow-xs transition-opacity hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed"
                  aria-label="Send message"
                >
                  <ArrowUp className="h-3.5 w-3.5 stroke-[2.5]" />
                </button>
              </div>
            </div>

            <div className="mt-2 text-center text-[10px] text-zinc-400 flex items-center justify-center gap-2">
              <ShieldCheck className="w-3 h-3 text-zinc-400" />
              <span>Real-time mutual fund intelligence powered by PostgreSQL & OpenUI. Press Enter to send.</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

