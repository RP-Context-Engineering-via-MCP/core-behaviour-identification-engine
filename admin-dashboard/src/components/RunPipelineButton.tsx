"use client";

import React, { useState } from "react";
import { Play } from "lucide-react";
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
        } catch (err: any) {
            setErrorMsg("Failed to start job");
            console.error(err);
        } finally {
            setIsStarting(false);
        }
    };

    const handleJobFinished = () => {
        if (onCompleted) {
            onCompleted();
        }
        // We optionally might un-set the active job ID after completion if we want to show the 'Run' button again,
        // but typically we'll leave it to show 'COMPLETED'.
    };

    if (activeJobId) {
        return <JobStatusBadge jobId={activeJobId} onCompleted={handleJobFinished} />;
    }

    return (
        <div className="flex items-center gap-2">
            <button
                onClick={handleRun}
                disabled={isStarting}
                className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50"
            >
                <Play className="h-4 w-4" />
                {isStarting ? "Starting..." : "Run CBIE"}
            </button>
            {errorMsg && <p className="text-xs text-red-600">{errorMsg}</p>}
        </div>
    );
}
