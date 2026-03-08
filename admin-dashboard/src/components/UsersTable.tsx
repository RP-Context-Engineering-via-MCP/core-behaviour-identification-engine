"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { UserDiscoveryItem } from "@/lib/types";
import { RunPipelineButton } from "./RunPipelineButton";

interface UsersTableProps {
    users: UserDiscoveryItem[];
    onMutate?: () => void;
}

export function UsersTable({ users, onMutate }: UsersTableProps) {
    const [searchTerm, setSearchTerm] = useState("");
    const [filter, setFilter] = useState<"ALL" | "NOT_ANALYZED" | "PROFILE_READY">("ALL");

    const filteredUsers = useMemo(() => {
        return users.filter((u) => {
            if (searchTerm && !u.user_id.toLowerCase().includes(searchTerm.toLowerCase())) return false;
            if (filter === "NOT_ANALYZED" && u.has_profile) return false;
            if (filter === "PROFILE_READY" && !u.has_profile) return false;
            return true;
        });
    }, [users, searchTerm, filter]);

    return (
        <div className="space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
                <input
                    type="text"
                    placeholder="Search user ID..."
                    className="h-9 w-64 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder-slate-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
                <select
                    className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value as typeof filter)}
                >
                    <option value="ALL">All users</option>
                    <option value="PROFILE_READY">Profile ready</option>
                    <option value="NOT_ANALYZED">Not analyzed</option>
                </select>
                {filteredUsers.length !== users.length && (
                    <span className="text-xs text-slate-400">
                        Showing {filteredUsers.length} of {users.length}
                    </span>
                )}
            </div>

            {/* Table */}
            <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
                <table className="min-w-full divide-y divide-slate-200">
                    <thead>
                        <tr className="bg-slate-50">
                            <th scope="col" className="py-3 pl-4 pr-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 sm:pl-6">
                                User
                            </th>
                            <th scope="col" className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                                Behaviors
                            </th>
                            <th scope="col" className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                                Status
                            </th>
                            <th scope="col" className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                                Profile summary
                            </th>
                            <th scope="col" className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                                Last updated
                            </th>
                            <th scope="col" className="relative py-3 pl-3 pr-4 sm:pr-6">
                                <span className="sr-only">Actions</span>
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {filteredUsers.map((user) => (
                            <tr key={user.user_id} className="transition-colors hover:bg-slate-50">
                                <td className="py-3.5 pl-4 pr-3 text-sm sm:pl-6">
                                    <Link
                                        href={`/admin/users/${user.user_id}`}
                                        className="font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
                                    >
                                        {user.user_id}
                                    </Link>
                                </td>
                                <td className="px-3 py-3.5 text-sm text-slate-600">
                                    <span className="font-medium text-slate-800 tabular-nums">{user.total_behaviors}</span>
                                    {user.last_behavior_at && (
                                        <span className="block text-xs text-slate-400 mt-0.5">
                                            {new Date(user.last_behavior_at).toLocaleDateString()}
                                        </span>
                                    )}
                                </td>
                                <td className="px-3 py-3.5 text-sm">
                                    {user.has_profile ? (
                                        <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-500/30">
                                            Analyzed
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-500 ring-1 ring-inset ring-slate-200">
                                            Pending
                                        </span>
                                    )}
                                </td>
                                <td className="px-3 py-3.5 text-sm text-slate-500">
                                    {user.has_profile ? (
                                        <div className="flex flex-wrap gap-x-2 gap-y-1 text-xs">
                                            <span className="font-medium text-slate-700">{user.profile_interest_count} total</span>
                                            <span className="text-rose-600">{user.profile_fact_count} facts</span>
                                            <span className="text-emerald-600">{user.profile_stable_count} stable</span>
                                            <span className="text-amber-600">{user.profile_emerging_count} emerging</span>
                                        </div>
                                    ) : (
                                        <span className="text-slate-300">—</span>
                                    )}
                                </td>
                                <td className="px-3 py-3.5 text-xs text-slate-400">
                                    {user.profile_last_updated
                                        ? new Date(user.profile_last_updated).toLocaleString()
                                        : <span className="text-slate-300">—</span>
                                    }
                                </td>
                                <td className="relative py-3.5 pl-3 pr-4 text-right text-sm sm:pr-6">
                                    {user.has_profile ? (
                                        <Link
                                            href={`/admin/users/${user.user_id}`}
                                            className="text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
                                        >
                                            View profile
                                        </Link>
                                    ) : (
                                        <RunPipelineButton userId={user.user_id} onCompleted={onMutate} />
                                    )}
                                </td>
                            </tr>
                        ))}
                        {filteredUsers.length === 0 && (
                            <tr>
                                <td colSpan={6} className="py-10 text-center text-sm text-slate-400">
                                    No users match the current filters.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
