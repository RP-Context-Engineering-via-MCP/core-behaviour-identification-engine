"use client";

import React from "react";
import { UserSummaryResponse } from "@/lib/types";
import { RunPipelineButton } from "./RunPipelineButton";
import { Calendar, Activity, CheckCircle2 } from "lucide-react";

interface UserDetailHeaderProps {
    summary: UserSummaryResponse;
    onRefresh: () => void;
}

export function UserDetailHeader({ summary, onRefresh }: UserDetailHeaderProps) {
    const { user_id, total_behaviors, last_behavior_at, has_profile, profile_summary } = summary;

    return (
        <div className="bg-white px-4 py-5 sm:px-6 shadow sm:rounded-lg">
            <div className="flex flex-wrap items-center justify-between sm:flex-nowrap">
                <div className="mb-4 sm:mb-0">
                    <h3 className="text-xl font-semibold leading-6 text-gray-900">
                        User: {user_id}
                    </h3>
                    <div className="mt-2 flex flex-col sm:flex-row sm:flex-wrap sm:space-x-6">
                        <div className="mt-2 flex items-center text-sm text-gray-500">
                            <Activity className="mr-1.5 h-4 w-4 flex-shrink-0 text-gray-400" />
                            {total_behaviors} Total Behaviors
                        </div>
                        {last_behavior_at && (
                            <div className="mt-2 flex items-center text-sm text-gray-500">
                                <Calendar className="mr-1.5 h-4 w-4 flex-shrink-0 text-gray-400" />
                                Last active {new Date(last_behavior_at).toLocaleDateString()}
                            </div>
                        )}
                        <div className="mt-2 flex items-center text-sm text-gray-500">
                            {has_profile ? (
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
                                    <CheckCircle2 className="h-3.5 w-3.5" />
                                    Profile Ready
                                </span>
                            ) : (
                                <span className="inline-flex items-center rounded-full bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
                                    Not Analyzed
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="ml-4 flex-shrink-0">
                    {/* If they have a profile, this acts as a 'Re-run' button. If not, standard run. */}
                    <RunPipelineButton
                        userId={user_id}
                        onCompleted={onRefresh}
                        initialJobId={profile_summary?.last_job_id}
                    />
                </div>
            </div>
        </div>
    );
}
