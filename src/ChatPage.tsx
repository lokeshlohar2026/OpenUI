import React, { useState, useRef, useEffect } from "react";
import { ChatMessage } from "./ChatMessage";
import {
  Send,
  Sparkles,
  Bot,
  User,
  Plus,
  Trash2,
  PieChart,
  BarChart3,
  TrendingUp,
  ShieldCheck,
  ChevronRight,
  Database,
  Zap,
  Layers,
} from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

const QUICK_PROMPTS = [
  {
    icon: <BarChart3 className="w-4 h-4 text-blue-600" />,
    title: "HDFC Flexi Cap Holdings",
    desc: "Top stock holdings & allocation breakdown",
    query: "Show portfolio holdings and market cap allocation for HDFC Flexi Cap Fund",
  },
  {
    icon: <TrendingUp className="w-4 h-4 text-emerald-600" />,
    title: "SBI Bluechip NAV Growth",
    desc: "Historical NAV growth & metrics",
    query: "Show SBI Bluechip Fund NAV growth history for the last 24 months with AUM and Riskometer",
  },
  {
    icon: <PieChart className="w-4 h-4 text-amber-600" />,
    title: "Nippon Small Cap Allocation",
    desc: "Market cap split & key holding metrics",
    query: "Show Market Cap allocation and top holdings for Nippon India Small Cap Fund",
  },
  {
    icon: <Layers className="w-4 h-4 text-purple-600" />,
    title: "ICICI Bluechip Factsheet",
    desc: "Fund overview KPIs & holdings table",
    query: "Provide a comprehensive factsheet with overview metrics and top holdings for ICICI Prudential Bluechip Fund",
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
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
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
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

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: textToSend }),
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

      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: "assistant",
          content: accumulated,
          timestamp: assistantTimestamp,
        },
      ]);
      setCurrentStream("");
    } catch (err) {
      console.error("Streaming error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: "assistant",
          content: `root = Column([TextContent("Error: Unable to load fund data from backend. Please verify FastAPI is running at :8000")])`,
          timestamp: assistantTimestamp,
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
    setMessages([]);
    setCurrentStream("");
    setInput("");
  };

  return (
    <div className="flex h-screen w-full bg-slate-50/60 font-sans text-slate-900 overflow-hidden antialiased">
      {/* ── Left Sidebar ──────────────────────────────────────────────── */}
      <aside
        className={`${
          isSidebarOpen ? "w-72" : "w-0 -translate-x-full"
        } transition-all duration-300 ease-in-out border-r border-slate-200/90 bg-white flex flex-col shrink-0 z-20 overflow-hidden`}
      >
        {/* Sidebar Header / Brand */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-slate-900 tracking-tight">MF Saarthi</h1>
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
            className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-blue-50 hover:bg-blue-100/80 text-blue-700 text-xs font-semibold border border-blue-200/60 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>New Analysis</span>
          </button>
        </div>

        {/* Quick Starters in Sidebar */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
          <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Suggested Analysis
          </div>
          {QUICK_PROMPTS.map((item, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(item.query)}
              disabled={loading}
              className="w-full text-left p-2.5 rounded-xl hover:bg-slate-100/80 text-xs transition-colors flex items-start gap-2.5 group border border-transparent hover:border-slate-200/60"
            >
              <div className="p-1 rounded-lg bg-slate-100 group-hover:bg-white transition-colors">
                {item.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-slate-800 truncate">{item.title}</div>
                <div className="text-[11px] text-slate-400 truncate">{item.desc}</div>
              </div>
            </button>
          ))}
        </div>

        {/* System Status Footer */}
        <div className="p-3.5 border-t border-slate-100 bg-slate-50/70 space-y-2">
          <div className="flex items-center justify-between text-[11px] text-slate-600">
            <span className="flex items-center gap-1.5 font-medium">
              <Database className="w-3.5 h-3.5 text-emerald-600" />
              Postgres DB
            </span>
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold text-[10px] border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              9.5M rows live
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-600">
            <span className="flex items-center gap-1.5 font-medium">
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              Groq Engine
            </span>
            <span className="text-[10px] font-mono text-slate-500 bg-slate-200/60 px-1.5 py-0.5 rounded">
              gpt-oss-20b
            </span>
          </div>
        </div>
      </aside>

      {/* ── Main Chat Area ────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col h-full bg-slate-50/40 relative min-w-0">
        {/* Top Navbar */}
        <header className="h-14 border-b border-slate-200/80 bg-white/90 backdrop-blur-md px-5 flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors"
              title="Toggle sidebar"
            >
              <Layers className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-800">Mutual Fund Intelligence</span>
              <span className="text-[11px] font-medium text-slate-500 hidden sm:inline-block">
                • OpenUI Reactive Interface
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={handleNewChat}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-rose-600 hover:bg-rose-50 rounded-lg border border-slate-200 transition-colors"
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
            {/* Empty State Welcome Screen */}
            {messages.length === 0 && !currentStream && (
              <div className="py-10 text-center space-y-6">
                <div className="w-14 h-14 rounded-2xl bg-blue-600 mx-auto flex items-center justify-center text-white shadow-xl shadow-blue-500/25">
                  <Sparkles className="w-7 h-7" />
                </div>
                <div className="space-y-1.5 max-w-md mx-auto">
                  <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                    Mutual Fund Copilot & Generative UI
                  </h2>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Ask any question about mutual funds, stock holdings, AUM history, and asset allocation. Live SQL data will be fetched and rendered into interactive charts.
                  </p>
                </div>

                {/* 4 Feature Starter Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto pt-2 text-left">
                  {QUICK_PROMPTS.map((card, i) => (
                    <div
                      key={i}
                      onClick={() => handleSend(card.query)}
                      className="p-4 rounded-2xl border border-slate-200 bg-white hover:border-blue-400 hover:shadow-md transition-all cursor-pointer group"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="p-2 rounded-xl bg-blue-50 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                          {card.icon}
                        </div>
                        <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all" />
                      </div>
                      <h3 className="font-semibold text-xs text-slate-800">{card.title}</h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">{card.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Conversation Messages */}
            {messages.map((msg) => (
              <div key={msg.id} className="space-y-2">
                {msg.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="max-w-2xl bg-slate-900 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm flex items-start gap-3">
                      <div className="text-xs leading-relaxed font-normal">{msg.content}</div>
                      <div className="w-5 h-5 rounded-full bg-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                        <User className="w-3 h-3 text-slate-200" />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="w-full">
                    <ChatMessage text={msg.content} timestamp={msg.timestamp} />
                  </div>
                )}
              </div>
            ))}

            {/* Live Streaming Message */}
            {currentStream && (
              <div className="w-full">
                <ChatMessage text={currentStream} isStreaming={true} timestamp="Streaming live…" />
              </div>
            )}

            {loading && !currentStream && (
              <div className="w-full bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex items-center gap-3 animate-pulse">
                <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center text-white">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="space-y-1.5 flex-1">
                  <div className="h-3 bg-slate-200 rounded w-48" />
                  <div className="h-2.5 bg-slate-100 rounded w-32" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* ── Bottom Floating Input Box ──────────────────────────────── */}
        <div className="p-4 bg-gradient-to-t from-slate-50 via-slate-50/95 to-transparent shrink-0">
          <div className="max-w-3xl mx-auto">
            {/* Quick Suggestion Pills */}
            {messages.length > 0 && !loading && (
              <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none text-[11px]">
                <span className="text-slate-400 shrink-0 font-medium">Try:</span>
                <button
                  onClick={() => handleSend("Show top holdings for SBI Small Cap Fund")}
                  className="px-2.5 py-1 rounded-full bg-white border border-slate-200 hover:border-blue-300 hover:text-blue-600 text-slate-600 shrink-0 transition-colors shadow-xs"
                >
                  SBI Small Cap Holdings
                </button>
                <button
                  onClick={() => handleSend("Show Market Cap allocation for Quant Active Fund")}
                  className="px-2.5 py-1 rounded-full bg-white border border-slate-200 hover:border-blue-300 hover:text-blue-600 text-slate-600 shrink-0 transition-colors shadow-xs"
                >
                  Quant Active Allocation
                </button>
                <button
                  onClick={() => handleSend("Compare HDFC Flexi Cap vs Parag Parikh Flexi Cap Fund")}
                  className="px-2.5 py-1 rounded-full bg-white border border-slate-200 hover:border-blue-300 hover:text-blue-600 text-slate-600 shrink-0 transition-colors shadow-xs"
                >
                  Flexi Cap Comparison
                </button>
              </div>
            )}

            {/* Input Container */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="relative flex items-end gap-2 bg-white border border-slate-300/90 focus-within:border-blue-500 focus-within:ring-3 focus-within:ring-blue-500/15 rounded-2xl p-2 shadow-md shadow-slate-200/50 transition-all"
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="Ask about any mutual fund (e.g., 'Show HDFC Flexi Cap holdings and NAV growth')..."
                className="w-full resize-none bg-transparent px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none max-h-40 leading-relaxed font-normal"
              />

              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="p-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-slate-200 text-white disabled:text-slate-400 transition-all shrink-0 shadow-sm shadow-blue-500/20 disabled:shadow-none"
                title="Send query"
              >
                {loading ? (
                  <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>

            <div className="mt-2 text-center text-[10px] text-slate-400 flex items-center justify-center gap-2">
              <ShieldCheck className="w-3 h-3 text-slate-400" />
              <span>Real-time mutual fund intelligence powered by PostgreSQL & OpenUI. Press Enter to send.</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
