// src/components/PipelineProgressBar.tsx
"use client";

import React from "react";
import { JobProgress } from "@/lib/types";

const STAGE_LABELS: Record<string, string> = {
    INGESTION_COMPLETE: "Behaviors ingested",
    FACT_ISOLATION: "Classifying behaviors",
    CLUSTERING_COMPLETE: "Clustering complete",
    TEMPORAL_ANALYSIS: "Temporal analysis",
    BUILDING_PROFILE: "Building profile",
};

interface PipelineProgressBarProps {
    progress: JobProgress;
}

export function PipelineProgressBar({ progress }: PipelineProgressBarProps) {
    const { stage, processed, total } = progress;
    const label = STAGE_LABELS[stage] ?? stage.replace(/_/g, " ").toLowerCase();

    // After ingestion completes, BART loads and runs its first batch silently.
    // Show an indeterminate shimmer bar so the user sees activity instead of a frozen bar.
    const isWarmingUp = stage === "INGESTION_COMPLETE";

    const pct = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;

    return (
        <div className="w-full min-w-[200px]">
            <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-slate-500 capitalize">
                    {isWarmingUp ? "Preparing classifier..." : label}
                </span>
                {!isWarmingUp && (
                    <span className="text-xs tabular-nums text-slate-600">
                        {processed} / {total}
                    </span>
                )}
            </div>
            <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                {isWarmingUp ? (
                    /* Indeterminate oscillating shimmer — CSS animation via Tailwind */
                    <div className="h-1.5 w-full relative overflow-hidden rounded-full bg-slate-100">
                        <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.4s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-indigo-400 to-transparent" />
                    </div>
                ) : (
                    <div
                        className="h-1.5 rounded-full bg-indigo-500 transition-all duration-300 ease-out"
                        style={{ width: `${pct}%` }}
                    />
                )}
            </div>
        </div>
    );
}
