// src/components/RunPipelineButton.tsx
"use client";

import React, { useState } from "react";
import { runPipeline } from "@/lib/api";
import { JobStatusBadge } from "./JobStatusBadge";

interface RunPipelineButtonProps {
    userId: string;
    onCompleted?: () => void;
    initialJobId?: string | null;
}

export function RunPipelineButton({ userId, onCompleted, initialJobId }: RunPipelineButtonProps) {
    const [activeJobId, setActiveJobId] = useState<string | null>(initialJobId || null);
    const [isStarting, setIsStarting] = useState(false);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    const handleRun = async () => {
        try {
            setIsStarting(true);
            setErrorMsg(null);
            const res = await runPipeline(userId);
            setActiveJobId(res.job_id);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to start analysis";
            setErrorMsg(msg);
        } finally {
            setIsStarting(false);
        }
    };

    const handleJobFinished = () => {
        onCompleted?.();
    };

    if (activeJobId) {
        return <JobStatusBadge jobId={activeJobId} onCompleted={handleJobFinished} />;
    }

    return (
        <div>
            <button
                onClick={handleRun}
                disabled={isStarting}
                className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
                {isStarting ? "Starting..." : "Run Analysis"}
            </button>
            {errorMsg && (
                <p className="mt-1 text-xs text-red-600">{errorMsg}</p>
            )}
        </div>
    );
}
