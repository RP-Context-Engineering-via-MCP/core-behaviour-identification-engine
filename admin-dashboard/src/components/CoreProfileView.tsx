// src/components/CoreProfileView.tsx
"use client";

import React, { useState } from "react";
import { CoreProfileDetailResponse, InterestEntry } from "@/lib/types";
import { Check, Copy } from "lucide-react";

// ── Status card used for each interest category ────────────────────────────────

interface StatusCardProps {
    title: string;
    items: InterestEntry[];
    accentClass: string; // Tailwind left-border color
    badgeClass: string;  // Tailwind badge bg color
}

const StatusCard = ({ title, items, accentClass, badgeClass }: StatusCardProps) => {
    if (items.length === 0) return null;

    return (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className={`border-l-4 ${accentClass} px-4 pt-4 pb-3`}>
                <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
                <p className="mt-0.5 text-xs text-slate-400">{items.length} item{items.length !== 1 ? "s" : ""}</p>
            </div>
            <ul className="divide-y divide-slate-100">
                {items.map((item, idx) => (
                    <li key={idx} className="px-4 py-3 flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-900 leading-snug">
                                {item.representative_topics.join(" · ")}
                            </p>
                            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-400">
                                <span>Frequency: {item.frequency}</span>
                                <span>Consistency: {item.consistency_score.toFixed(2)}</span>
                                <span>Trend: {item.trend_score.toFixed(2)}</span>
                            </div>
                        </div>
                        <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${badgeClass}`}>
                            {item.core_score.toFixed(2)}
                        </span>
                    </li>
                ))}
            </ul>
        </div>
    );
};

// ── Copy-to-clipboard button ──────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium text-slate-500 ring-1 ring-inset ring-slate-200 hover:bg-slate-50 transition-colors"
        >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
        </button>
    );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function CoreProfileView({ profile }: { profile: CoreProfileDetailResponse }) {
    return (
        <div className="space-y-6 mt-4">

            {/* Identity Anchor Prompt */}
            {profile.identity_anchor_prompt && (
                <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
                    <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                        <div>
                            <h3 className="text-sm font-semibold text-slate-800">Identity Anchor Prompt</h3>
                            <p className="mt-0.5 text-xs text-slate-400">
                                Ready-to-inject system prompt for LLM personalization
                            </p>
                        </div>
                        <CopyButton text={profile.identity_anchor_prompt} />
                    </div>
                    <pre className="p-4 text-xs leading-relaxed text-slate-700 font-mono whitespace-pre-wrap break-words bg-slate-50 max-h-64 overflow-y-auto">
                        {profile.identity_anchor_prompt}
                    </pre>
                </div>
            )}

            {/* Summary row */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                    { label: "Critical Constraints", value: profile.critical_constraints.length, color: "text-rose-600" },
                    { label: "Stable Interests", value: profile.stable_interests.length, color: "text-emerald-600" },
                    { label: "Emerging Interests", value: profile.emerging_interests.length, color: "text-amber-600" },
                    { label: "Archived Patterns", value: profile.archived_core.length, color: "text-slate-500" },
                ].map(({ label, value, color }) => (
                    <div key={label} className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
                        <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
                        <p className="mt-0.5 text-xs text-slate-500">{label}</p>
                    </div>
                ))}
            </div>

            {/* Interest cards grid */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <StatusCard
                    title="Critical Constraints"
                    items={profile.critical_constraints}
                    accentClass="border-rose-500"
                    badgeClass="bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200"
                />
                <StatusCard
                    title="Stable Interests"
                    items={profile.stable_interests}
                    accentClass="border-emerald-500"
                    badgeClass="bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200"
                />
                <StatusCard
                    title="Emerging Interests"
                    items={profile.emerging_interests}
                    accentClass="border-amber-400"
                    badgeClass="bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200"
                />
                <StatusCard
                    title="Archived Patterns"
                    items={profile.archived_core}
                    accentClass="border-slate-300"
                    badgeClass="bg-slate-50 text-slate-600 ring-1 ring-inset ring-slate-200"
                />
            </div>

            {/* Noise summary */}
            <p className="text-xs text-slate-400">
                {profile.noise_summary.noise_count} behavior{profile.noise_summary.noise_count !== 1 ? "s" : ""} classified as noise
                &nbsp;&middot;&nbsp;
                {profile.noise_summary.archived_count} archived
                &nbsp;&middot;&nbsp;
                {profile.total_raw_behaviors} total behaviors analyzed
            </p>
        </div>
    );
}
