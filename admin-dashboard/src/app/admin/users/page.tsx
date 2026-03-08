"use client";

import React from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { UserDiscoveryResponse } from "@/lib/types";
import { UsersTable } from "@/components/UsersTable";
import { Loader2, AlertCircle } from "lucide-react";

export default function UsersPage() {
    const { data, error, isLoading } = useSWR<UserDiscoveryResponse>(
        "/admin/users",
        fetcher
    );

    return (
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
            <div className="sm:flex sm:items-center">
                <div className="sm:flex-auto">
                    <h1 className="text-2xl font-semibold leading-6 text-gray-900">
                        CBIE User Discovery
                    </h1>
                    <p className="mt-2 text-sm text-gray-700">
                        A list of all users with recorded behaviors. You can monitor their
                        profile readiness and trigger the NLP pipeline manually.
                    </p>
                </div>
            </div>

            <div className="mt-8">
                {isLoading && (
                    <div className="flex items-center justify-center p-12 text-gray-500">
                        <Loader2 className="h-8 w-8 animate-spin" />
                        <span className="ml-3">Loading users...</span>
                    </div>
                )}

                {error && (
                    <div className="rounded-md bg-red-50 p-4">
                        <div className="flex">
                            <div className="flex-shrink-0">
                                <AlertCircle className="h-5 w-5 text-red-400" aria-hidden="true" />
                            </div>
                            <div className="ml-3">
                                <h3 className="text-sm font-medium text-red-800">
                                    Error loading users
                                </h3>
                                <div className="mt-2 text-sm text-red-700">
                                    <p>
                                        Could not connect to the CBIE FastAPI backend. Make sure it is
                                        running on port 8000.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {data && <UsersTable users={data.users} />}
            </div>
        </div>
    );
}
