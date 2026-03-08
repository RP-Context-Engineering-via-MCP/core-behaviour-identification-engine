// src/components/PipelineProgressBar.tsx
"use client";

import React from "react";
import { JobProgress } from "@/lib/types";

const STAGE_LABELS: Record<string, string> = {
    INGESTION_COMPLETE: "Ingestion",
    FACT_ISOLATION: "Classifying behaviors",
    CLUSTERING_COMPLETE: "Clustering",
    TEMPORAL_ANALYSIS: "Temporal analysis",
};

interface PipelineProgressBarProps {
    progress: JobProgress;
}

export function PipelineProgressBar({ progress }: PipelineProgressBarProps) {
    const { stage, processed, total } = progress;
    const pct = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
    const label = STAGE_LABELS[stage] ?? stage.replace(/_/g, " ").toLowerCase();

    return (
        <div className="w-full min-w-[180px]">
            <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-slate-500 capitalize">{label}</span>
                <span className="text-xs tabular-nums text-slate-600">
                    {processed} / {total}
                </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                    className="h-1.5 rounded-full bg-indigo-500 transition-all duration-300 ease-out"
                    style={{ width: `${pct}%` }}
                />
            </div>
        </div>
    );
}
