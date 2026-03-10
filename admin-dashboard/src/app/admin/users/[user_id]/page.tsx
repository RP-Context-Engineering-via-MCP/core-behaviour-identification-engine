"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/api";
import { UserSummaryResponse, CoreProfileDetailResponse } from "@/lib/types";
import { CoreProfileView } from "@/components/CoreProfileView";
import { BehaviorPreviewTable } from "@/components/BehaviorPreviewTable";
import { RunPipelineButton } from "@/components/RunPipelineButton";
import { Loader2, AlertCircle, ChevronLeft } from "lucide-react";

type Tab = "profile" | "debug";

export default function UserDetailPage() {
    const { user_id: userId } = useParams<{ user_id: string }>();
    const [activeTab, setActiveTab] = useState<Tab>("profile");

    // 1. User summary
    const {
        data: summary,
        error: summaryError,
        isLoading: summaryLoading,
        mutate: mutateSummary,
    } = useSWR<UserSummaryResponse>(`/admin/users/${userId}`, fetcher);

    // 2. Core profile — only when summary says profile exists
    const {
        data: profile,
        error: profileError,
        isLoading: profileLoading,
        mutate: mutateProfile,
    } = useSWR<CoreProfileDetailResponse>(
        summary?.has_profile ? `/admin/users/${userId}/profile` : null,
        fetcher
    );

    const handleRefresh = () => {
        mutateSummary();
        mutateProfile();
    };

    // ── Loading state ─────────────────────────────────────────────────────────
    if (summaryLoading) {
        return (
            <div className="flex h-64 items-center justify-center text-slate-400">
                <Loader2 className="h-6 w-6 animate-spin mr-2.5" />
                <span className="text-sm">Loading user data...</span>
            </div>
        );
    }

    // ── Error / not found ─────────────────────────────────────────────────────
    if (summaryError || !summary) {
        return (
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 shadow-sm">
                    <div className="flex gap-3">
                        <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 shrink-0" />
                        <div>
                            <p className="text-sm font-medium text-red-800">User not found</p>
                            <p className="mt-1 text-xs text-red-600">
                                No data was found for <code className="font-mono">{userId}</code>
                            </p>
                            <Link href="/admin/users" className="mt-2 inline-block text-xs font-medium text-red-700 underline">
                                Back to directory
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // ── Main content ──────────────────────────────────────────────────────────
    return (
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">

            {/* Breadcrumb */}
            <Link
                href="/admin/users"
                className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-slate-700 transition-colors mb-5"
            >
                <ChevronLeft className="h-3.5 w-3.5" />
                All users
            </Link>

            {/* Page header */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-6">
                <div>
                    <h1 className="text-xl font-semibold text-slate-900 font-mono">{userId}</h1>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                        <span>{summary.total_behaviors.toLocaleString()} behaviors</span>
                        {summary.last_behavior_at && (
                            <span>Last recorded {new Date(summary.last_behavior_at).toLocaleDateString()}</span>
                        )}
                        {summary.has_profile ? (
                            <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-500/30">
                                Profile ready
                            </span>
                        ) : (
                            <span className="inline-flex items-center rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
                                Not analyzed
                            </span>
                        )}
                    </div>
                </div>

                {/* Run pipeline button */}
                <RunPipelineButton userId={userId} onCompleted={handleRefresh} />
            </div>

            {/* Profile summary stats row */}
            {summary.profile_summary && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-6">
                    {[
                        { label: "Total behaviors", value: summary.profile_summary.total_raw_behaviors },
                        { label: "Core interests", value: summary.profile_summary.interest_count },
                        { label: "Stable interests", value: summary.profile_summary.stable_count },
                        { label: "Active facts", value: summary.profile_summary.fact_count },
                    ].map(({ label, value }) => (
                        <div key={label} className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
                            <p className="text-xl font-bold tabular-nums text-slate-800">{value}</p>
                            <p className="mt-0.5 text-xs text-slate-400">{label}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* Pill tabs */}
            <div className="flex gap-1.5 rounded-lg bg-slate-100 p-1 w-fit mb-6">
                {(["profile", "debug"] as Tab[]).map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${activeTab === tab
                                ? "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200"
                                : "text-slate-500 hover:text-slate-700"
                            }`}
                    >
                        {tab === "profile" ? "Core Profile" : "Raw Behaviors"}
                    </button>
                ))}
            </div>

            {/* Tab content */}
            {activeTab === "profile" && (
                <>
                    {!summary.has_profile && (
                        <div className="rounded-lg border border-slate-200 bg-white py-12 px-4 text-center shadow-sm">
                            <p className="text-sm font-medium text-slate-700">No profile has been generated yet</p>
                            <p className="mt-1 text-xs text-slate-400">
                                Click &ldquo;Run Analysis&rdquo; above to begin the CBIE pipeline.
                            </p>
                        </div>
                    )}
                    {summary.has_profile && profileLoading && (
                        <div className="flex items-center gap-2 py-8 text-slate-400">
                            <Loader2 className="h-5 w-5 animate-spin" />
                            <span className="text-sm">Loading profile details...</span>
                        </div>
                    )}
                    {summary.has_profile && profileError && (
                        <p className="text-sm text-red-500 flex items-center gap-2">
                            <AlertCircle className="h-4 w-4" />
                            Failed to load profile details.
                        </p>
                    )}
                    {summary.has_profile && profile && <CoreProfileView profile={profile} />}
                </>
            )}

            {activeTab === "debug" && <BehaviorPreviewTable userId={userId} />}
        </div>
    );
}
