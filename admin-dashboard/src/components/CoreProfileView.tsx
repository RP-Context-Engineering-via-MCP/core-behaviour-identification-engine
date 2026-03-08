import React from "react";
import { CoreProfileDetailResponse, InterestEntry } from "@/lib/types";

// Helper components for the different status lists
const StatusCard = ({ title, items, colorClass }: { title: string, items: InterestEntry[], colorClass: string }) => {
    if (items.length === 0) return null;

    return (
        <div className={`overflow-hidden rounded-lg bg-white shadow ring-1 ${colorClass}`}>
            <div className={`px-4 py-5 sm:px-6 border-b ${colorClass.replace('ring-1', 'bg-opacity-10')}`}>
                <h3 className="text-base font-semibold leading-6 text-gray-900">{title}</h3>
            </div>
            <ul role="list" className="divide-y divide-gray-100 p-4">
                {items.map((item, idx) => (
                    <li key={idx} className="flex flex-col gap-x-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold leading-6 text-gray-900">
                                {item.representative_topics.join(" • ")}
                            </p>
                            <div className="mt-1 flex items-center gap-x-2 text-xs leading-5 text-gray-500">
                                <p className="truncate">Freq: {item.frequency}</p>
                                <svg viewBox="0 0 2 2" className="h-0.5 w-0.5 fill-current"><circle cx={1} cy={1} r={1} /></svg>
                                <p className="truncate">Cons:: {item.consistency_score.toFixed(2)}</p>
                                <svg viewBox="0 0 2 2" className="h-0.5 w-0.5 fill-current"><circle cx={1} cy={1} r={1} /></svg>
                                <p className="truncate">Trend: {item.trend_score.toFixed(2)}</p>
                            </div>
                        </div>
                        <div className="mt-2 flex flex-none items-center gap-x-2 sm:mt-0">
                            <span className="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
                                Score: {item.core_score.toFixed(2)}
                            </span>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
};

export function CoreProfileView({ profile }: { profile: CoreProfileDetailResponse }) {
    return (
        <div className="space-y-8 mt-6">

            {/* Identity Anchor Prompt */}
            {profile.identity_anchor_prompt && (
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <h3 className="text-sm font-semibold text-gray-900 mb-2">Compiled Identity Anchor Prompt</h3>
                    <textarea
                        readOnly
                        className="w-full bg-white text-sm text-gray-800 p-3 rounded-md border border-gray-300 font-mono shadow-inner resize-y h-48 focus:outline-none"
                        value={profile.identity_anchor_prompt}
                    />
                </div>
            )}

            {/* Grid of Interests */}
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                {/* Critical Constraints */}
                <StatusCard
                    title="Critical Constraints (Stable Facts)"
                    items={profile.critical_constraints}
                    colorClass="ring-rose-200"
                />

                {/* Stable Interests */}
                <StatusCard
                    title="Stable Interests"
                    items={profile.stable_interests}
                    colorClass="ring-emerald-200"
                />

                {/* Emerging Interests */}
                <StatusCard
                    title="Emerging Interests"
                    items={profile.emerging_interests}
                    colorClass="ring-amber-200"
                />

                {/* Archived Core */}
                <StatusCard
                    title="Archived Patterns"
                    items={profile.archived_core}
                    colorClass="ring-gray-200"
                />
            </div>

        </div>
    );
}
