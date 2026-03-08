// src/lib/types.ts

// ---------------------------------------------------------------------------
// Shared / Reusable sub-models
// ---------------------------------------------------------------------------

export type InterestStatus = "Stable" | "Emerging" | "Stable Fact" | "ARCHIVED_CORE" | "Noise";

export interface InterestEntry {
    cluster_id: string | number;
    representative_topics: string[];
    frequency: number;
    consistency_score: number;
    trend_score: number;
    core_score: number;
    status: InterestStatus;
}


// ---------------------------------------------------------------------------
// /admin/users
// ---------------------------------------------------------------------------

export interface UserDiscoveryItem {
    user_id: string;
    total_behaviors: number;
    last_behavior_at?: string;
    has_profile: boolean;
    profile_interest_count?: number;
    profile_stable_count?: number;
    profile_emerging_count?: number;
    profile_fact_count?: number;
    profile_last_updated?: string;
}

export interface UserDiscoveryResponse {
    total_users: number;
    users: UserDiscoveryItem[];
}


// ---------------------------------------------------------------------------
// /admin/users/{user_id}
// ---------------------------------------------------------------------------

export interface ProfileSummaryStats {
    total_raw_behaviors: number;
    interest_count: number;
    stable_count: number;
    emerging_count: number;
    fact_count: number;
    last_updated?: string;
    last_job_id?: string;
}

export interface UserSummaryResponse {
    user_id: string;
    total_behaviors: number;
    last_behavior_at?: string;
    has_profile: boolean;
    profile_summary?: ProfileSummaryStats;
}


// ---------------------------------------------------------------------------
// /admin/users/{user_id}/profile
// ---------------------------------------------------------------------------

export interface NoiseSummary {
    noise_count: number;
    archived_count: number;
}

export interface CoreProfileDetailResponse {
    user_id: string;
    total_raw_behaviors: number;
    critical_constraints: InterestEntry[];
    stable_interests: InterestEntry[];
    emerging_interests: InterestEntry[];
    archived_core: InterestEntry[];
    noise_summary: NoiseSummary;
    identity_anchor_prompt?: string;
    last_updated?: string;
}


// ---------------------------------------------------------------------------
// /admin/users/{user_id}/run_pipeline and jobs
// ---------------------------------------------------------------------------

export interface PipelineRunResponse {
    job_id: string;
    status: string;
    user_id: string;
    message: string;
}

export interface AdminJobStatusResponse {
    job_id: string;
    user_id: string;
    status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
    started_at?: string;
    completed_at?: string;
    error?: string;
}


// ---------------------------------------------------------------------------
// /admin/users/{user_id}/behaviors
// ---------------------------------------------------------------------------

export interface BehaviorPreviewItem {
    behavior_id?: string;
    created_at?: string;
    behavior_text: string;
    intent?: string;
    target?: string;
    context?: string;
    polarity?: string;
    behavior_state?: string;
    credibility?: number;
    clarity_score?: number;
    extraction_confidence?: number;
}

export interface BehaviorPreviewResponse {
    user_id: string;
    total: number;
    behaviors: BehaviorPreviewItem[];
}
