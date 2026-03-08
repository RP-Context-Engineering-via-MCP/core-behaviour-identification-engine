"use client";

import React, { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/api";
import { UserSummaryResponse, CoreProfileDetailResponse } from "@/lib/types";
import { UserDetailHeader } from "@/components/UserDetailHeader";
import { CoreProfileView } from "@/components/CoreProfileView";
import { BehaviorPreviewTable } from "@/components/BehaviorPreviewTable";
import { Loader2, AlertCircle, ArrowLeft } from "lucide-react";

export default function UserDetailPage({ params }: { params: { user_id: string } }) {
    const userId = params.user_id;

    // 1. Fetch User Summary
    const {
        data: summary,
        error: summaryError,
        isLoading: summaryLoading,
        mutate: mutateSummary
    } = useSWR<UserSummaryResponse>(`/admin/users/${userId}`, fetcher);

    // 2. Conditionally Fetch Profile Detail
    const hasProfile = summary?.has_profile;
    const {
        data: profile,
        error: profileError,
        isLoading: profileLoading,
        mutate: mutateProfile
    } = useSWR<CoreProfileDetailResponse>(
        hasProfile ? `/admin/users/${userId}/profile` : null,
        fetcher
    );

    const [activeTab, setActiveTab] = useState<"profile" | "debug">("profile");

    const handleRefresh = () => {
        mutateSummary();
        mutateProfile();
    };

    if (summaryLoading) {
        return (
            <div className="flex h-screen items-center justify-center text-gray-400">
                <Loader2 className="h-8 w-8 animate-spin mr-3" /> Loading user data...
            </div>
        );
    }

    if (summaryError || !summary) {
        return (
            <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
                <div className="rounded-md bg-red-50 p-4">
                    <div className="flex">
                        <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 mr-3" />
                        <div>
                            <h3 className="text-sm font-medium text-red-800">User not found</h3>
                            <div className="mt-2 text-sm text-red-700">Could not read summary for {userId}</div>
                            <Link href="/admin/users" className="mt-3 block text-sm font-medium text-red-900 underline hover:text-red-700">
                                &larr; Back to directory
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
            <Link href="/admin/users" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-700 mb-6">
                <ArrowLeft className="mr-1.5 h-4 w-4" /> Back to users
            </Link>

            <UserDetailHeader summary={summary} onRefresh={handleRefresh} />

            <div className="mt-8 border-b border-gray-200">
                <nav className="-mb-px flex space-x-8" aria-label="Tabs">
                    <button
                        onClick={() => setActiveTab("profile")}
                        className={`
              ${activeTab === "profile"
                                ? "border-indigo-500 text-indigo-600"
                                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"}
              whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium
            `}
                    >
                        Core Profile Details
                    </button>
                    <button
                        onClick={() => setActiveTab("debug")}
                        className={`
              ${activeTab === "debug"
                                ? "border-indigo-500 text-indigo-600"
                                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"}
              whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium
            `}
                    >
                        Debug (Raw Behaviors)
                    </button>
                </nav>
            </div>

            <div className="mt-6">
                {activeTab === "profile" && (
                    <>
                        {!hasProfile && (
                            <div className="text-center bg-gray-50 border border-gray-200 rounded-lg py-12 px-4 shadow-sm">
                                <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
                                <h3 className="mt-2 text-sm font-semibold text-gray-900">No profile generated</h3>
                                <p className="mt-1 text-sm text-gray-500">
                                    Click "Run CBIE" above to analyze this user's logs and build their identity anchor.
                                </p>
                            </div>
                        )}
                        {hasProfile && profileLoading && (
                            <div className="flex justify-center p-8"><Loader2 className="h-6 w-6 animate-spin text-gray-400" /></div>
                        )}
                        {hasProfile && profileError && (
                            <div className="text-red-500 text-sm">Error loading profile details.</div>
                        )}
                        {hasProfile && profile && (
                            <CoreProfileView profile={profile} />
                        )}
                    </>
                )}

                {activeTab === "debug" && <BehaviorPreviewTable userId={userId} />}
            </div>
        </div>
    );
}
