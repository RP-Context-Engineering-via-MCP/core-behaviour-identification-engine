"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
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
    Users,
    RefreshCw,
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

interface UserItem {
    user_id: string;
    total_behaviors: number;
    has_profile: boolean;
    profile_interest_count?: number;
}

interface UsersApiResponse {
    total_users: number;
    users: UserItem[];
}

// ─── Lightweight Markdown → HTML ─────────────────────────────────────────────

function mdToHtml(md: string): string {
    let html = md
        // Escape HTML entities
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        // Code blocks
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="bg-slate-800 text-slate-100 rounded-lg p-3 my-2 overflow-x-auto text-xs"><code>$2</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code class="bg-slate-100 text-indigo-700 rounded px-1.5 py-0.5 text-xs font-mono">$1</code>')
        // Headers
        .replace(/^### (.+)$/gm, '<h3 class="text-sm font-semibold mb-1 mt-2">$1</h3>')
        .replace(/^## (.+)$/gm, '<h2 class="text-sm font-bold mb-1.5 mt-2.5">$1</h2>')
        .replace(/^# (.+)$/gm, '<h1 class="text-base font-bold mb-2 mt-3">$1</h1>')
        // Bold & italic
        .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Unordered lists
        .replace(/^[\-\*] (.+)$/gm, '<li class="leading-relaxed ml-4 list-disc">$1</li>')
        // Ordered lists
        .replace(/^\d+\. (.+)$/gm, '<li class="leading-relaxed ml-4 list-decimal">$1</li>')
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-indigo-600 underline hover:text-indigo-800">$1</a>')
        // Blockquotes
        .replace(/^> (.+)$/gm, '<blockquote class="border-l-2 border-indigo-300 pl-3 my-1 text-slate-600 italic">$1</blockquote>')
        // Horizontal rules
        .replace(/^---$/gm, '<hr class="my-3 border-slate-200" />')
        // Line breaks → paragraphs
        .replace(/\n\n+/g, '</p><p class="mb-2">')
        .replace(/\n/g, '<br />');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/((?:<li[^>]*>.*?<\/li>\s*(?:<br \/>)?\s*)+)/g, '<ul class="list-disc pl-4 mb-2 space-y-1">$1</ul>');
    // Clean up <br /> inside <ul>
    html = html.replace(/<ul[^>]*>([\s\S]*?)<\/ul>/g, (match) => match.replace(/<br \/>/g, ''));

    return `<p class="mb-2">${html}</p>`;
}

function MarkdownContent({ content }: { content: string }) {
    const html = useMemo(() => mdToHtml(content), [content]);
    return <div className="prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: html }} />;
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
    const [userId, setUserId] = useState("");
    const [useContext, setUseContext] = useState(true);
    const [input, setInput] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bottomRef = useRef<HTMLDivElement>(null);

    // User dropdown state
    const [users, setUsers] = useState<UserItem[]>([]);
    const [usersLoading, setUsersLoading] = useState(true);
    const [usersError, setUsersError] = useState<string | null>(null);
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const fetchUsers = useCallback(async () => {
        setUsersLoading(true);
        setUsersError(null);
        try {
            const res = await apiClient.get<UsersApiResponse>("/admin/users");
            const sortedUsers = res.data.users.sort((a, b) => a.user_id.localeCompare(b.user_id));
            setUsers(sortedUsers);
            if (!userId && sortedUsers.length > 0) {
                // Auto-select first user with a profile, or first user
                const withProfile = sortedUsers.find(u => u.has_profile);
                setUserId((withProfile || sortedUsers[0]).user_id);
            }
        } catch {
            setUsersError("Failed to load users");
        } finally {
            setUsersLoading(false);
        }
    }, [userId]);

    useEffect(() => { fetchUsers(); }, [fetchUsers]);

    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setDropdownOpen(false);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    const sendMessage = async () => {
        if (!input.trim() || loading || !userId) return;
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

    const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const selectedUser = users.find(u => u.user_id === userId);

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
                                    Chat Demo
                                </h1>
                                <p className="text-xs text-slate-500">
                                    Powered by CBIE context injection
                                </p>
                            </div>
                        </div>

                        {/* Controls */}
                        <div className="flex flex-wrap items-center gap-3">
                            {/* User dropdown */}
                            <div className="relative" ref={dropdownRef}>
                                <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1">
                                    User
                                </label>
                                <button
                                    onClick={() => setDropdownOpen(!dropdownOpen)}
                                    disabled={usersLoading}
                                    className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 shadow-sm hover:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-400 min-w-[200px] transition-colors"
                                >
                                    <Users className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                                    {usersLoading ? (
                                        <span className="text-slate-400 flex items-center gap-1">
                                            <Loader2 className="h-3 w-3 animate-spin" /> Loading…
                                        </span>
                                    ) : usersError ? (
                                        <span className="text-red-500">{usersError}</span>
                                    ) : userId ? (
                                        <span className="truncate flex-1 text-left">{userId}</span>
                                    ) : (
                                        <span className="text-slate-400">Select a user…</span>
                                    )}
                                    <ChevronDown className={`h-3 w-3 text-slate-400 shrink-0 transition-transform ${dropdownOpen ? "rotate-180" : ""}`} />
                                </button>

                                {dropdownOpen && !usersLoading && users.length > 0 && (
                                    <div className="absolute top-full left-0 mt-1 w-72 max-h-64 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg z-50">
                                        <div className="p-1.5">
                                            {users.map((u) => (
                                                <button
                                                    key={u.user_id}
                                                    onClick={() => { setUserId(u.user_id); setDropdownOpen(false); }}
                                                    className={`w-full flex items-center justify-between gap-2 rounded-md px-3 py-2 text-xs transition-colors ${
                                                        u.user_id === userId
                                                            ? "bg-indigo-50 text-indigo-700 font-medium"
                                                            : "text-slate-700 hover:bg-slate-50"
                                                    }`}
                                                >
                                                    <div className="flex items-center gap-2 min-w-0">
                                                        <User className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                                                        <span className="truncate">{u.user_id}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2 shrink-0">
                                                        <span className="text-[10px] text-slate-400">{u.total_behaviors} behaviors</span>
                                                        {u.has_profile ? (
                                                            <span className="flex h-4 items-center rounded-full bg-emerald-50 px-1.5 text-[10px] font-medium text-emerald-700 border border-emerald-200">
                                                                Profile ✓
                                                            </span>
                                                        ) : (
                                                            <span className="flex h-4 items-center rounded-full bg-slate-50 px-1.5 text-[10px] text-slate-400 border border-slate-200">
                                                                No profile
                                                            </span>
                                                        )}
                                                    </div>
                                                </button>
                                            ))}
                                        </div>
                                        <div className="border-t border-slate-100 p-1.5">
                                            <button
                                                onClick={() => { fetchUsers(); }}
                                                className="w-full flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-[11px] text-slate-500 hover:bg-slate-50 transition-colors"
                                            >
                                                <RefreshCw className="h-3 w-3" /> Refresh list
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Context toggle */}
                            <div>
                                <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1">
                                    Context
                                </label>
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
                                    <strong>Context ON:</strong> The LLM is given the CBIE identity anchor prompt for{" "}
                                    <strong>{userId || "—"}</strong>. Responses will be personalised to their long-term
                                    interests and constraints.
                                    {selectedUser && !selectedUser.has_profile && (
                                        <span className="ml-1 text-amber-700 font-medium">
                                            ⚠ This user has no profile yet — run the pipeline first for context injection to work.
                                        </span>
                                    )}
                                </>
                            ) : (
                                <>
                                    <strong>Context OFF:</strong> The LLM sees only your message — no CBIE profile
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
                                CBIE profile personalises the LLM&apos;s responses.
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
                                            ? "LLM + CBIE context"
                                            : "LLM (no context)"}
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
                                    {m.role === "assistant" ? (
                                        <MarkdownContent content={m.content} />
                                    ) : (
                                        m.content
                                    )}
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
                    <div className="flex items-end gap-3">
                        <div
                            className={`flex h-2 w-2 rounded-full shrink-0 mb-3 ${useContext ? "bg-indigo-500 animate-pulse" : "bg-slate-300"
                                }`}
                        />
                        <div className="flex flex-1 items-end gap-2 rounded-2xl border border-slate-200 bg-white shadow-sm px-4 py-2.5 focus-within:ring-2 focus-within:ring-indigo-400">
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKey}
                                placeholder={
                                    !userId
                                        ? "Select a user first…"
                                        : useContext
                                            ? `Ask something personalised for ${userId}…`
                                            : "Ask anything (no personalisation)…"
                                }
                                className="flex-1 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400 resize-none max-h-32"
                                disabled={loading || !userId}
                                rows={1}
                                onInput={(e) => {
                                    const el = e.target as HTMLTextAreaElement;
                                    el.style.height = "auto";
                                    el.style.height = Math.min(el.scrollHeight, 128) + "px";
                                }}
                            />
                            <button
                                onClick={sendMessage}
                                disabled={!input.trim() || loading || !userId}
                                className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-white transition-all hover:bg-indigo-700 disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
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
                        <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] ml-1">Shift+Enter</kbd> for new line •
                        Toggle context to compare personalised vs. baseline responses
                    </p>
                </div>
            </div>
        </div>
    );
}
