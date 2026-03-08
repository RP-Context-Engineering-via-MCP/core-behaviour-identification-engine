"use client";

import React, { useState } from "react";
import Link from "next/link";
import { UserDiscoveryItem } from "@/lib/types";
import { RunPipelineButton } from "./RunPipelineButton";

interface UsersTableProps {
    users: UserDiscoveryItem[];
}

export function UsersTable({ users }: UsersTableProps) {
    const [searchTerm, setSearchTerm] = useState("");
    const [filter, setFilter] = useState<"ALL" | "NOT_ANALYZED" | "PROFILE_READY">("ALL");

    const filteredUsers = users.filter((u) => {
        if (searchTerm && !u.user_id.toLowerCase().includes(searchTerm.toLowerCase())) return false;
        if (filter === "NOT_ANALYZED" && u.has_profile) return false;
        if (filter === "PROFILE_READY" && !u.has_profile) return false;
        return true;
    });

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-4">
                <input
                    type="text"
                    placeholder="Search by user ID..."
                    className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-64 text-black bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
                <select
                    className="border border-gray-300 rounded-md xl:w-48 px-3 py-1.5 text-sm text-black bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value as any)}
                >
                    <option value="ALL">All Users</option>
                    <option value="PROFILE_READY">Profile Ready</option>
                    <option value="NOT_ANALYZED">Not Analyzed</option>
                </select>
            </div>

            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
                <table className="min-w-full divide-y divide-gray-300 bg-white">
                    <thead className="bg-gray-50">
                        <tr>
                            <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">
                                User ID
                            </th>
                            <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                                Behaviors
                            </th>
                            <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                                Status
                            </th>
                            <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                                Profile Stats
                            </th>
                            <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                                Last Updated
                            </th>
                            <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                                <span className="sr-only">Actions</span>
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                        {filteredUsers.map((user) => (
                            <tr key={user.user_id}>
                                <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                                    <Link href={`/admin/users/${user.user_id}`} className="text-indigo-600 hover:text-indigo-900">
                                        {user.user_id}
                                    </Link>
                                </td>
                                <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                    {user.total_behaviors}
                                    {user.last_behavior_at && (
                                        <span className="block text-xs text-gray-400">
                                            {new Date(user.last_behavior_at).toLocaleDateString()}
                                        </span>
                                    )}
                                </td>
                                <td className="whitespace-nowrap px-3 py-4 text-sm">
                                    {user.has_profile ? (
                                        <span className="inline-flex items-center rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
                                            Analyzed
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center rounded-full bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
                                            Pending
                                        </span>
                                    )}
                                </td>
                                <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                    {user.has_profile ? (
                                        <div className="flex gap-2">
                                            <span title="Items" className="text-gray-900 font-medium">{user.profile_interest_count} Items</span>
                                            <span title="Facts" className="text-red-700">({user.profile_fact_count})</span>
                                            <span title="Stable" className="text-green-700">({user.profile_stable_count})</span>
                                            <span title="Emerging" className="text-amber-600">({user.profile_emerging_count})</span>
                                        </div>
                                    ) : (
                                        "-"
                                    )}
                                </td>
                                <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                    {user.profile_last_updated ? new Date(user.profile_last_updated).toLocaleString() : "-"}
                                </td>
                                <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                                    {user.has_profile ? (
                                        <Link href={`/admin/users/${user.user_id}`} className="text-indigo-600 hover:text-indigo-900 mr-4">
                                            View Details
                                        </Link>
                                    ) : (
                                        <RunPipelineButton userId={user.user_id} />
                                    )}
                                </td>
                            </tr>
                        ))}
                        {filteredUsers.length === 0 && (
                            <tr>
                                <td colSpan={6} className="py-8 text-center text-sm text-gray-500">
                                    No users found matching the filters.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
