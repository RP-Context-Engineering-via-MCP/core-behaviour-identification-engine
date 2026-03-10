"use client";

import { useState, useRef, useEffect } from "react";
import { apiClient } from "@/lib/api";
import {
    Brain,
    BrainCircuit,
    Send,
    Loader2,
    User,
    Bot,
    Sparkles,
    Info,
    ChevronDown,
    ChevronUp,
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface Message {
    role: "user" | "assistant";
    content: string;
    useContext: boolean;
    contextUsed?: string | null;
}

interface ChatApiResponse {
    reply: string;
    user_id: string;
    use_context: boolean;
    context_used: string | null;
}

// ─── Context Preview Card ────────────────────────────────────────────────────

function ContextPreview({ text }: { text: string }) {
    const [open, setOpen] = useState(false);
    return (
        <div className="mt-2 rounded-lg border border-indigo-200 bg-indigo-50 text-xs">
            <button
                onClick={() => setOpen(!open)}
                className="flex w-full items-center justify-between gap-2 px-3 py-2 text-indigo-700 font-medium"
            >
                <span className="flex items-center gap-1.5">
                    <Sparkles className="h-3 w-3" /> CBIE context injected
                </span>
                {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
            {open && (
                <div className="border-t border-indigo-200 px-3 py-2 text-indigo-900 leading-relaxed whitespace-pre-wrap">
                    {text}
                </div>
            )}
        </div>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function ChatDemoPage() {
    const [userId, setUserId] = useState("pilot_user_1");
    const [useContext, setUseContext] = useState(true);
    const [input, setInput] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;
        const userMsg = input.trim();
        setInput("");
        setError(null);

        setMessages((prev) => [
            ...prev,
            { role: "user", content: userMsg, useContext },
        ]);
        setLoading(true);

        try {
            const res = await apiClient.post<ChatApiResponse>("/chat", {
                user_id: userId,
                message: userMsg,
                use_context: useContext,
            });
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: res.data.reply,
                    useContext: res.data.use_context,
                    contextUsed: res.data.context_used,
                },
            ]);
        } catch (err: unknown) {
            const msg = (err as { response?: { data?: { detail?: string } }, message?: string })
                ?.response?.data?.detail ?? (err as { message?: string })?.message ?? "Unknown error";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="flex flex-col min-h-[calc(100vh-56px)] bg-gradient-to-br from-slate-50 to-indigo-50/30">
            {/* ── Header ───────────────────────────────────────────────────── */}
            <div className="border-b border-slate-200 bg-white/80 backdrop-blur-sm">
                <div className="mx-auto max-w-4xl px-4 py-4 sm:px-6">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        {/* Title */}
                        <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 shadow-sm">
                                <BrainCircuit className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <h1 className="text-base font-semibold text-slate-900">
                                    Gemini Chat Demo
                                </h1>
                                <p className="text-xs text-slate-500">
                                    Powered by CBIE context injection
                                </p>
                            </div>
                        </div>

                        {/* Controls */}
                        <div className="flex flex-wrap items-center gap-3">
                            {/* User selector */}
                            <div className="flex items-center gap-2">
                                <label className="text-xs font-medium text-slate-600">
                                    User ID
                                </label>
                                <input
                                    value={userId}
                                    onChange={(e) => setUserId(e.target.value)}
                                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 w-44"
                                    placeholder="e.g. pilot_user_1"
                                />
                            </div>

                            {/* Context toggle */}
                            <button
                                onClick={() => setUseContext(!useContext)}
                                className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-200 shadow-sm ${useContext
                                        ? "bg-indigo-600 text-white hover:bg-indigo-700 ring-2 ring-indigo-400/30"
                                        : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                                    }`}
                            >
                                {useContext ? (
                                    <Brain className="h-4 w-4" />
                                ) : (
                                    <Bot className="h-4 w-4" />
                                )}
                                <span>{useContext ? "Context ON" : "Context OFF"}</span>
                                <span
                                    className={`ml-1 flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold ${useContext ? "bg-white/20" : "bg-slate-200"
                                        }`}
                                >
                                    {useContext ? "✓" : "✗"}
                                </span>
                            </button>
                        </div>
                    </div>

                    {/* Context mode info banner */}
                    <div
                        className={`mt-3 rounded-lg px-3 py-2 text-xs flex items-start gap-2 transition-colors ${useContext
                                ? "bg-indigo-50 text-indigo-800 border border-indigo-200"
                                : "bg-slate-100 text-slate-600 border border-slate-200"
                            }`}
                    >
                        <Info className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                        <span>
                            {useContext ? (
                                <>
                                    <strong>Context ON:</strong> Gemini is given the CBIE identity anchor prompt for{" "}
                                    <strong>{userId}</strong>. Responses will be personalised to their long-term
                                    interests and constraints.
                                </>
                            ) : (
                                <>
                                    <strong>Context OFF:</strong> Gemini sees only your message — no CBIE profile
                                    injected. This is the baseline, unpersonalised response.
                                </>
                            )}
                        </span>
                    </div>
                </div>
            </div>

            {/* ── Chat area ────────────────────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto">
                <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 space-y-6">
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-20 text-center">
                            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white border border-slate-200 shadow-sm mb-4">
                                <Sparkles className="h-8 w-8 text-indigo-400" />
                            </div>
                            <h2 className="text-lg font-semibold text-slate-700">
                                Try the context toggle
                            </h2>
                            <p className="mt-1 text-sm text-slate-500 max-w-sm">
                                Ask the same question with Context ON and OFF to see how the
                                CBIE profile personalises Gemini&apos;s responses.
                            </p>
                            <div className="mt-4 flex flex-wrap justify-center gap-2">
                                {[
                                    "What technology should I learn next?",
                                    "Recommend me a good meal.",
                                    "What should I focus on in my career?",
                                    "Suggest a hobby for the weekend.",
                                ].map((s) => (
                                    <button
                                        key={s}
                                        onClick={() => setInput(s)}
                                        className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700 transition-colors"
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {messages.map((m, i) => (
                        <div
                            key={i}
                            className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                            {m.role === "assistant" && (
                                <div
                                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${m.useContext ? "bg-indigo-600" : "bg-slate-400"
                                        }`}
                                >
                                    {m.useContext ? (
                                        <Brain className="h-4 w-4 text-white" />
                                    ) : (
                                        <Bot className="h-4 w-4 text-white" />
                                    )}
                                </div>
                            )}

                            <div className={`max-w-[80%] ${m.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
                                {/* Role label */}
                                <span className={`mb-1 text-[11px] font-medium ${m.role === "user" ? "text-slate-400 text-right" : m.useContext ? "text-indigo-500" : "text-slate-400"
                                    }`}>
                                    {m.role === "user"
                                        ? "You"
                                        : m.useContext
                                            ? "Gemini + CBIE context"
                                            : "Gemini (no context)"}
                                </span>

                                {/* Bubble */}
                                <div
                                    className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${m.role === "user"
                                            ? "bg-indigo-600 text-white rounded-tr-sm"
                                            : m.useContext
                                                ? "bg-white border border-indigo-100 text-slate-800 rounded-tl-sm"
                                                : "bg-white border border-slate-200 text-slate-700 rounded-tl-sm"
                                        }`}
                                >
                                    {m.content}
                                </div>

                                {/* Context accordion */}
                                {m.role === "assistant" && m.contextUsed && (
                                    <ContextPreview text={m.contextUsed} />
                                )}
                            </div>

                            {m.role === "user" && (
                                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200">
                                    <User className="h-4 w-4 text-slate-600" />
                                </div>
                            )}
                        </div>
                    ))}

                    {loading && (
                        <div className="flex gap-3 justify-start">
                            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${useContext ? "bg-indigo-600" : "bg-slate-400"}`}>
                                <Brain className="h-4 w-4 text-white animate-pulse" />
                            </div>
                            <div className="rounded-2xl rounded-tl-sm bg-white border border-slate-200 px-4 py-3 shadow-sm flex items-center gap-2 text-slate-400 text-sm">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Thinking…
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="mx-auto max-w-lg rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                            <strong>Error:</strong> {error}
                        </div>
                    )}

                    <div ref={bottomRef} />
                </div>
            </div>

            {/* ── Input bar ────────────────────────────────────────────────── */}
            <div className="border-t border-slate-200 bg-white/80 backdrop-blur-sm">
                <div className="mx-auto max-w-4xl px-4 py-3 sm:px-6">
                    <div className="flex items-center gap-3">
                        <div
                            className={`flex h-2 w-2 rounded-full shrink-0 ${useContext ? "bg-indigo-500 animate-pulse" : "bg-slate-300"
                                }`}
                        />
                        <div className="flex flex-1 items-center gap-2 rounded-2xl border border-slate-200 bg-white shadow-sm px-4 py-2.5 focus-within:ring-2 focus-within:ring-indigo-400">
                            <input
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKey}
                                placeholder={
                                    useContext
                                        ? `Ask something personalised for ${userId}…`
                                        : "Ask anything (no personalisation)…"
                                }
                                className="flex-1 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
                                disabled={loading}
                            />
                            <button
                                onClick={sendMessage}
                                disabled={!input.trim() || loading}
                                className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-white transition-all hover:bg-indigo-700 disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                                {loading ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                    <Send className="h-3.5 w-3.5" />
                                )}
                            </button>
                        </div>
                    </div>
                    <p className="mt-2 text-center text-[11px] text-slate-400">
                        Press <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px]">Enter</kbd> to send •
                        Toggle context to compare personalised vs. baseline Gemini responses
                    </p>
                </div>
            </div>
        </div>
    );
}
