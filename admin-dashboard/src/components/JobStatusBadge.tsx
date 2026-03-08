// src/components/JobStatusBadge.tsx
"use client";

import React from "react";
import useSWR from "swr";
import { Loader2, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { fetcher } from "@/lib/api";
import { AdminJobStatusResponse } from "@/lib/types";
import { PipelineProgressBar } from "./PipelineProgressBar";

interface JobStatusBadgeProps {
    jobId: string;
    onCompleted?: () => void;
}

export function JobStatusBadge({ jobId, onCompleted }: JobStatusBadgeProps) {
    const { data, error } = useSWR<AdminJobStatusResponse>(
        jobId ? `/admin/jobs/${jobId}` : null,
        fetcher,
        {
            // Poll every 1.5 s while active — fast enough for a progress bar to look smooth
            refreshInterval: (data) =>
                data && (data.status === "QUEUED" || data.status === "RUNNING") ? 1500 : 0,
            dedupingInterval: 500,
            onSuccess: (data) => {
                if (data.status === "COMPLETED" || data.status === "FAILED") {
                    onCompleted?.();
                }
            },
        }
    );

    if (error) {
        return (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/20">
                <AlertCircle className="h-3.5 w-3.5" />
                Connection error
            </span>
        );
    }

    if (!data) {
        return (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-200">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Connecting...
            </span>
        );
    }

    switch (data.status) {
        case "QUEUED":
            return (
                <span className="inline-flex items-center gap-1.5 rounded-md bg-amber-50 px-2.5 py-1.5 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
                    <Clock className="h-3.5 w-3.5" />
                    Queued
                </span>
            );

        case "RUNNING":
            // Show live progress bar if progress data is available, otherwise fallback badge
            if (data.progress) {
                return (
                    <div className="flex items-center gap-3 min-w-[220px]">
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-500 shrink-0" />
                        <PipelineProgressBar progress={data.progress} />
                    </div>
                );
            }
            return (
                <span className="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2.5 py-1.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-200">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Running...
                </span>
            );

        case "COMPLETED":
            return (
                <span className="inline-flex items-center gap-1.5 rounded-md bg-emerald-50 px-2.5 py-1.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-500/30">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Profile ready
                </span>
            );

        case "FAILED":
            return (
                <span
                    className="inline-flex items-center gap-1.5 rounded-md bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/20"
                    title={data.error ?? "Unknown error"}
                >
                    <AlertCircle className="h-3.5 w-3.5" />
                    Failed — hover for details
                </span>
            );

        default:
            return null;
    }
}
