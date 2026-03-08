"use client";

import React from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { UserDiscoveryResponse } from "@/lib/types";
import { UsersTable } from "@/components/UsersTable";
import { Loader2, AlertCircle } from "lucide-react";

export default function UsersPage() {
    const { data, error, isLoading, mutate } = useSWR<UserDiscoveryResponse>(
        "/admin/users",
        fetcher,
        { dedupingInterval: 30_000 }
    );

    const totalBehaviors = data?.users.reduce((s, u) => s + u.total_behaviors, 0) ?? 0;
    const analyzedCount = data?.users.filter((u) => u.has_profile).length ?? 0;

    return (
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">

            {/* Page header */}
            <div className="mb-6">
                <h1 className="text-xl font-semibold text-slate-900">User Discovery</h1>
                <p className="mt-1 text-sm text-slate-500">
                    {isLoading ? "Loading..." : (
                        <>
                            {data?.total_users ?? 0} users &middot; {analyzedCount} analyzed &middot; {totalBehaviors.toLocaleString()} total behaviors
                        </>
                    )}
                </p>
            </div>

            {/* States */}
            {isLoading && (
                <div className="flex items-center justify-center rounded-lg border border-slate-200 bg-white py-16 text-slate-400 shadow-sm">
                    <Loader2 className="h-5 w-5 animate-spin mr-2.5" />
                    <span className="text-sm">Fetching user data...</span>
                </div>
            )}

            {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 shadow-sm">
                    <div className="flex gap-3">
                        <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 shrink-0" />
                        <div>
                            <p className="text-sm font-medium text-red-800">Could not connect to the backend</p>
                            <p className="mt-1 text-xs text-red-600">
                                Make sure the CBIE FastAPI server is running on port 8000.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {data && (
                <UsersTable
                    users={data.users}
                    onMutate={() => mutate()}
                />
            )}
        </div>
    );
}
