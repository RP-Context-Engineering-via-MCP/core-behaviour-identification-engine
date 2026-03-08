"use client";

import React from "react";
import useSWR from "swr";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { fetcher } from "@/lib/api";
import { AdminJobStatusResponse } from "@/lib/types";

interface JobStatusBadgeProps {
    jobId: string;
    onCompleted?: () => void;
}

export function JobStatusBadge({ jobId, onCompleted }: JobStatusBadgeProps) {
    const { data, error } = useSWR<AdminJobStatusResponse>(
        jobId ? `/admin/jobs/${jobId}` : null,
        fetcher,
        {
            refreshInterval: (data) =>
                data && (data.status === "QUEUED" || data.status === "RUNNING") ? 2000 : 0,
            onSuccess: (data) => {
                if (data.status === "COMPLETED" || data.status === "FAILED") {
                    onCompleted?.();
                }
            },
        }
    );

    if (error) {
        return (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                <AlertCircle className="h-3.5 w-3.5" />
                Error Fetching Job
            </span>
        );
    }

    if (!data) {
        return (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-800">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Loading...
            </span>
        );
    }

    switch (data.status) {
        case "QUEUED":
        case "RUNNING":
            return (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    {data.status === "RUNNING" ? "Analyzing..." : "Queued"}
                </span>
            );
        case "COMPLETED":
            return (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Profile Ready
                </span>
            );
        case "FAILED":
            return (
                <span
                    className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800"
                    title={data.error || "Unknown Error"}
                >
                    <AlertCircle className="h-3.5 w-3.5" />
                    Failed
                </span>
            );
        default:
            return null;
    }
}
