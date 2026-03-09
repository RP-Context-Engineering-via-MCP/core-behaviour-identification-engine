// src/components/EmbeddingScatterPlot.tsx
"use client";

import React, { useMemo } from "react";
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    ZAxis,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from "recharts";
import { EmbeddingPoint } from "@/lib/types";

// ── Status colours ─────────────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
    "Stable Fact": "#ef4444",  // rose-500
    "Stable": "#22c55e",  // green-500
    "Emerging": "#f59e0b",  // amber-500
    "ARCHIVED_CORE": "#94a3b8",  // slate-400
    "CONTRADICTED": "#a855f7",  // purple-500
    "Noise": "#cbd5e1",  // slate-300
};

function statusColor(status: string): string {
    return STATUS_COLORS[status] ?? "#cbd5e1";
}

// ── Custom tooltip ──────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: { payload: EmbeddingPoint }[] }) => {
    if (!active || !payload?.length) return null;
    const pt = payload[0].payload;
    return (
        <div className="max-w-xs rounded-lg border border-slate-200 bg-white px-3.5 py-3 shadow-lg text-xs">
            <p className="font-semibold text-slate-800 mb-1 truncate">{pt.label || "Unlabeled cluster"}</p>
            <p className="text-slate-500 line-clamp-3 leading-relaxed">{pt.text}</p>
            <div className="mt-2 flex items-center gap-2">
                <span
                    className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: statusColor(pt.status) }}
                />
                <span className="text-slate-400">{pt.status}</span>
                <span className="text-slate-300">cluster {pt.cluster_id}</span>
            </div>
        </div>
    );
};

// ── Main Component ──────────────────────────────────────────────────────────────
export function EmbeddingScatterPlot({ points }: { points: EmbeddingPoint[] }) {
    // Group points by status for separate Scatter series (each gets its own legend entry + colour)
    const groups = useMemo(() => {
        const map: Record<string, EmbeddingPoint[]> = {};
        for (const p of points) {
            const key = p.status || "Noise";
            if (!map[key]) map[key] = [];
            map[key].push(p);
        }
        // Sort so facts / stable / emerging come first, noise last
        const order = ["Stable Fact", "Stable", "Emerging", "ARCHIVED_CORE", "CONTRADICTED", "Noise"];
        return Object.entries(map).sort(
            ([a], [b]) => (order.indexOf(a) > -1 ? order.indexOf(a) : 99) - (order.indexOf(b) > -1 ? order.indexOf(b) : 99)
        );
    }, [points]);

    if (!points.length) {
        return (
            <div className="flex h-48 items-center justify-center text-sm text-slate-400">
                No embedding data available. Re-run the pipeline to generate the map.
            </div>
        );
    }

    return (
        <div className="w-full">
            <ResponsiveContainer width="100%" height={360}>
                <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: -16 }}>
                    <XAxis
                        dataKey="x"
                        type="number"
                        name="t-SNE x"
                        tick={{ fontSize: 10, fill: "#94a3b8" }}
                        tickLine={false}
                        axisLine={false}
                        domain={["auto", "auto"]}
                    />
                    <YAxis
                        dataKey="y"
                        type="number"
                        name="t-SNE y"
                        tick={{ fontSize: 10, fill: "#94a3b8" }}
                        tickLine={false}
                        axisLine={false}
                        domain={["auto", "auto"]}
                    />
                    {/* ZAxis sets the dot size */}
                    <ZAxis range={[28, 28]} />
                    <Tooltip content={<CustomTooltip />} cursor={false} />
                    <Legend
                        iconType="circle"
                        iconSize={9}
                        wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
                    />
                    {groups.map(([status, pts]) => (
                        <Scatter
                            key={status}
                            name={status}
                            data={pts}
                            fill={statusColor(status)}
                            fillOpacity={status === "Noise" ? 0.35 : 0.75}
                            strokeWidth={0}
                        />
                    ))}
                </ScatterChart>
            </ResponsiveContainer>
            <p className="mt-1 text-center text-xs text-slate-400">
                {points.length} behaviors &middot; each dot is one behavior, colored by its confirmed status
            </p>
        </div>
    );
}
