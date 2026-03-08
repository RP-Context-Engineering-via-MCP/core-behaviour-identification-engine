"use client";

import React from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { BehaviorPreviewResponse } from "@/lib/types";
import { Loader2, AlertCircle } from "lucide-react";

export function BehaviorPreviewTable({ userId }: { userId: string }) {
    const { data, error, isLoading } = useSWR<BehaviorPreviewResponse>(
        `/admin/users/${userId}/behaviors?limit=50&offset=0`,
        fetcher
    );

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-8 text-gray-400">
                <Loader2 className="h-6 w-6 animate-spin mr-2" /> Loading raw behaviors...
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="text-sm text-red-500 p-4 bg-red-50 rounded-md flex items-center mt-6">
                <AlertCircle className="w-4 h-4 mr-2" /> Error loading behaviors
            </div>
        );
    }

    return (
        <div className="mt-8 flow-root">
            <h3 className="text-base font-semibold leading-6 text-gray-900 mb-4">
                Raw Behavioral Data Preview (Limit 50)
            </h3>

            <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
                    <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
                        <table className="min-w-full divide-y divide-gray-300">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6 w-1/2">
                                        Behavior Text
                                    </th>
                                    <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                                        Intent
                                    </th>
                                    <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                                        Context / Target
                                    </th>
                                    <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                                        State
                                    </th>
                                    <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                                        Recorded
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 bg-white">
                                {data.behaviors.map((beh) => (
                                    <tr key={beh.behavior_id}>
                                        <td className="whitespace-normal py-4 pl-4 pr-3 text-sm text-gray-900 sm:pl-6">
                                            {beh.behavior_text}
                                        </td>
                                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                            {beh.intent}
                                            {beh.polarity === "NEGATIVE" && (
                                                <span className="ml-2 inline-flex items-center rounded-md bg-red-50 px-1.5 py-0.5 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/10">NEG</span>
                                            )}
                                        </td>
                                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                            {beh.context} <br />
                                            <span className="text-xs text-gray-400">{beh.target}</span>
                                        </td>
                                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                            {beh.behavior_state === "ACTIVE" ? (
                                                <span className="text-green-600 font-medium">ACTIVE</span>
                                            ) : (
                                                <span className="text-gray-400">{beh.behavior_state}</span>
                                            )}
                                        </td>
                                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                            {beh.created_at ? new Date(beh.created_at).toLocaleDateString() : ""}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
