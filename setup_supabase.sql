-- Supabase SQL Editor Script (v2)
-- Run this to RESET and recreate the behaviors table with the full schema

DROP TABLE IF EXISTS public.behaviors;

CREATE TABLE public.behaviors (
    behavior_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    behavior_text TEXT,
    embedding vector(384),
    credibility REAL DEFAULT 0.5,
    extraction_confidence REAL DEFAULT 0.5,
    clarity_score REAL DEFAULT 0.5,
    linguistic_strength REAL,
    decay_rate REAL,
    reinforcement_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    prompt_history_ids TEXT,
    behavior_state TEXT,
    superseded_by_id TEXT,
    related_behaviors TEXT,
    last_decay_applied_at TIMESTAMP WITH TIME ZONE,
    context_notes TEXT,
    intent TEXT,
    target TEXT,
    context TEXT,
    polarity TEXT,
    last_accessed_at TIMESTAMP WITH TIME ZONE
);

-- Create index for fast user lookups
CREATE INDEX idx_behaviors_user_id ON public.behaviors(user_id);

-- ============================================================
-- Core Behavior Profiles Table
-- ============================================================
DROP TABLE IF EXISTS public.core_behavior_profiles;

CREATE TABLE public.core_behavior_profiles (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    total_raw_behaviors INTEGER DEFAULT 0,
    confirmed_interests JSONB DEFAULT '[]'::jsonb,
    identity_anchor_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_profiles_user_id ON public.core_behavior_profiles(user_id);

-- Optional: Enable Row Level Security
-- ALTER TABLE public.behaviors ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.core_behavior_profiles ENABLE ROW LEVEL SECURITY;
