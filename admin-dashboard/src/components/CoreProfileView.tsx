// src/components/CoreProfileView.tsx
"use client";

import React, { useState } from "react";
import useSWR from "swr";
import { CoreProfileDetailResponse, InterestEntry, EmbeddingMapResponse } from "@/lib/types";
import { Check, Copy, Loader2, AlertCircle } from "lucide-react";
import { fetcher } from "@/lib/api";
import { EmbeddingScatterPlot } from "./EmbeddingScatterPlot";
import { RadarScoreChart } from "./RadarScoreChart";

// ── Interest Status Card ──────────────────────────────────────────────────────

interface StatusCardProps {
    title: string;
    items: InterestEntry[];
    accentClass: string;
    badgeClass: string;
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
                                <span>Credibility: {(item.avg_credibility ?? 0.5).toFixed(2)}</span>
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

// ── Copy-to-clipboard ──────────────────────────────────────────────────────────

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

// ── Section wrapper with title ─────────────────────────────────────────────────

function ChartSection({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
    return (
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="border-b border-slate-100 px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
                {description && <p className="mt-0.5 text-xs text-slate-400">{description}</p>}
            </div>
            <div className="px-4 py-4">
                {children}
            </div>
        </div>
    );
}

// ── Main Export ────────────────────────────────────────────────────────────────

export function CoreProfileView({ profile }: { profile: CoreProfileDetailResponse }) {
    // Fetch embedding map — this may 404 for older profiles; we handle it gracefully
    const { data: embeddingData, isLoading: embLoading } = useSWR<EmbeddingMapResponse>(
        `/admin/users/${profile.user_id}/embedding-map`,
        fetcher,
        { shouldRetryOnError: false, dedupingInterval: 60_000 }
    );

    // Combine all non-noise interests for the radar chart
    const allConfirmed: InterestEntry[] = [
        ...profile.critical_constraints,
        ...profile.stable_interests,
        ...profile.emerging_interests,
    ];

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

            {/* Summary stat row */}
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

            {/* ── Charts row ─────────────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">

                {/* Radar / Pentagon scoring chart */}
                <ChartSection
                    title="Profile Scoring Radar"
                    description="AHP dimensions for each confirmed interest cluster — all values normalized 0 to 1"
                >
                    {allConfirmed.length > 0 ? (
                        <RadarScoreChart interests={allConfirmed} />
                    ) : (
                        <div className="flex h-48 items-center justify-center text-sm text-slate-400">
                            No confirmed interests to plot.
                        </div>
                    )}
                </ChartSection>

                {/* 2D t-SNE embedding scatter */}
                <ChartSection
                    title="Behavior Embedding Map"
                    description="t-SNE projection of all behavior embeddings — clusters that are semantically similar appear close together"
                >
                    {embLoading ? (
                        <div className="flex h-48 items-center justify-center gap-2 text-sm text-slate-400">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Computing layout...
                        </div>
                    ) : embeddingData ? (
                        <EmbeddingScatterPlot points={embeddingData.points} />
                    ) : (
                        <div className="flex h-48 flex-col items-center justify-center gap-2 text-center">
                            <AlertCircle className="h-5 w-5 text-slate-300" />
                            <p className="text-sm text-slate-400">
                                No embedding map found.
                            </p>
                            <p className="text-xs text-slate-300">
                                Re-run the pipeline to generate it.
                            </p>
                        </div>
                    )}
                </ChartSection>
            </div>

            {/* ── Interest cards ─────────────────────────────────────────────────── */}
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

            {/* Noise footer */}
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
