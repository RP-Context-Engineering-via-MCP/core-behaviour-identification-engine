// src/components/RadarScoreChart.tsx
"use client";

import React from "react";
import {
    RadarChart,
    Radar,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from "recharts";
import { InterestEntry } from "@/lib/types";

// ── Colours per cluster ────────────────────────────────────────────────────────
const SERIES_COLORS = [
    "#6366f1", // indigo
    "#22c55e", // green
    "#f59e0b", // amber
    "#ef4444", // rose
    "#a855f7", // purple
    "#0ea5e9", // sky
];

// ── Axes (the 5 scoring dimensions we have) ────────────────────────────────────
const AXES = [
    { key: "core_score", label: "Core Score" },
    { key: "consistency_score", label: "Consistency" },
    { key: "trend_score_norm", label: "Trend" },
    { key: "avg_credibility", label: "Credibility" },
    { key: "frequency_norm", label: "Frequency" },
] as const;

// ── Normalize incoming entry into 0-1 values for all axes ───────────────────────
function normalizeEntry(entry: InterestEntry, maxFreq: number) {
    return {
        label: entry.representative_topics[0] ?? `Cluster ${entry.cluster_id}`,
        core_score: Math.min(1, Math.max(0, entry.core_score)),
        consistency_score: Math.min(1, Math.max(0, entry.consistency_score)),
        // trend_score is -1..1 → normalise to 0..1
        trend_score_norm: Math.min(1, Math.max(0, (entry.trend_score + 1) / 2)),
        avg_credibility: Math.min(1, Math.max(0, entry.avg_credibility ?? 0.5)),
        frequency_norm: maxFreq > 0 ? Math.min(1, entry.frequency / maxFreq) : 0,
    };
}

// ── Radar data format recharts expects: one object per axis ────────────────────
function buildRadarData(normalizedEntries: ReturnType<typeof normalizeEntry>[]) {
    return AXES.map(({ key, label }) => {
        const row: Record<string, number | string> = { axis: label };
        normalizedEntries.forEach((e, idx) => {
            row[`series_${idx}`] = (e as Record<string, number | string>)[key] as number;
        });
        return row;
    });
}

// ── Custom tooltip ──────────────────────────────────────────────────────────────
const CustomTooltip = ({
    active, payload, label
}: {
    active?: boolean;
    payload?: { name: string; value: number }[];
    label?: string;
}) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-lg text-xs">
            <p className="font-semibold text-slate-700 mb-1.5">{label}</p>
            {payload.map((p) => (
                <div key={p.name} className="flex items-center gap-2">
                    <span className="text-slate-500 font-medium">{p.value.toFixed(2)}</span>
                </div>
            ))}
        </div>
    );
};

// ── Main Component ──────────────────────────────────────────────────────────────
interface RadarScoreChartProps {
    interests: InterestEntry[];
    /** Only show interests with this status (if undefined, show all confirmed) */
    statuses?: string[];
}

export function RadarScoreChart({ interests, statuses }: RadarScoreChartProps) {
    const filtered = interests.filter((i) =>
        !statuses || statuses.includes(i.status)
    );

    if (!filtered.length) {
        return (
            <div className="flex h-48 items-center justify-center text-sm text-slate-400">
                No confirmed interests to display.
            </div>
        );
    }

    const maxFreq = Math.max(...filtered.map((e) => e.frequency));
    const normalized = filtered.map((e) => normalizeEntry(e, maxFreq));
    const radarData = buildRadarData(normalized);

    return (
        <div className="w-full">
            <ResponsiveContainer width="100%" height={340}>
                <RadarChart data={radarData} margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis
                        dataKey="axis"
                        tick={{ fontSize: 11, fill: "#64748b", fontWeight: 500 }}
                    />
                    <PolarRadiusAxis
                        angle={90}
                        domain={[0, 1]}
                        tick={{ fontSize: 9, fill: "#cbd5e1" }}
                        tickCount={4}
                        axisLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        iconType="circle"
                        iconSize={9}
                        wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
                    />
                    {normalized.map((entry, idx) => (
                        <Radar
                            key={entry.label}
                            name={entry.label.length > 28 ? entry.label.slice(0, 28) + "…" : entry.label}
                            dataKey={`series_${idx}`}
                            stroke={SERIES_COLORS[idx % SERIES_COLORS.length]}
                            fill={SERIES_COLORS[idx % SERIES_COLORS.length]}
                            fillOpacity={0.12}
                            strokeWidth={1.5}
                            dot={false}
                        />
                    ))}
                </RadarChart>
            </ResponsiveContainer>
            <p className="mt-1 text-center text-xs text-slate-400">
                All metrics normalized 0 – 1 &middot; trend: -1..1 remapped &middot; frequency: relative to top cluster
            </p>
        </div>
    );
}
