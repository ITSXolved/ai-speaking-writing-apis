-- Migration: Add skill mastery tracking tables
-- Description: Creates tables for tracking skill-level performance in sessions and user mastery
-- Date: 2025-10-06

-- ============================================================
-- TABLE: lrg_session_skills
-- Stores skill breakdown for each session
-- ============================================================

CREATE TABLE IF NOT EXISTS lrg_session_skills (
    skill_record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES lrg_sessions(session_id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    correct INTEGER NOT NULL CHECK (correct >= 0),
    total INTEGER NOT NULL CHECK (total > 0),
    mastery_pct INTEGER NOT NULL CHECK (mastery_pct >= 0 AND mastery_pct <= 100),
    mastery_level TEXT NOT NULL CHECK (mastery_level IN ('beginner', 'developing', 'proficient', 'advanced')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_session_skill UNIQUE (session_id, skill)
);

-- Index for faster session skill lookups
CREATE INDEX IF NOT EXISTS idx_session_skills_session_id ON lrg_session_skills(session_id);
CREATE INDEX IF NOT EXISTS idx_session_skills_skill ON lrg_session_skills(skill);


-- ============================================================
-- TABLE: lrg_skill_mastery
-- Stores cumulative skill mastery per user and modality
-- ============================================================

CREATE TABLE IF NOT EXISTS lrg_skill_mastery (
    mastery_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    modality TEXT NOT NULL CHECK (modality IN ('listening', 'reading', 'grammar')),
    skill TEXT NOT NULL,
    total_attempts INTEGER NOT NULL DEFAULT 0 CHECK (total_attempts >= 0),
    correct_attempts INTEGER NOT NULL DEFAULT 0 CHECK (correct_attempts >= 0),
    mastery_pct INTEGER NOT NULL DEFAULT 0 CHECK (mastery_pct >= 0 AND mastery_pct <= 100),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_user_modality_skill UNIQUE (user_id, modality, skill)
);

-- Indexes for faster user mastery lookups
CREATE INDEX IF NOT EXISTS idx_skill_mastery_user_id ON lrg_skill_mastery(user_id);
CREATE INDEX IF NOT EXISTS idx_skill_mastery_modality ON lrg_skill_mastery(modality);
CREATE INDEX IF NOT EXISTS idx_skill_mastery_user_modality ON lrg_skill_mastery(user_id, modality);
CREATE INDEX IF NOT EXISTS idx_skill_mastery_skill ON lrg_skill_mastery(skill);


-- ============================================================
-- ALTER TABLE: lrg_answers
-- Add skill column to existing answers table
-- ============================================================

-- Add skill column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'lrg_answers'
        AND column_name = 'skill'
    ) THEN
        ALTER TABLE lrg_answers ADD COLUMN skill TEXT;
    END IF;
END $$;

-- Index for skill filtering in answers
CREATE INDEX IF NOT EXISTS idx_answers_skill ON lrg_answers(skill);


-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE lrg_session_skills IS 'Skill-level breakdown for each completed session';
COMMENT ON TABLE lrg_skill_mastery IS 'Cumulative skill mastery tracking per user and modality';
COMMENT ON COLUMN lrg_answers.skill IS 'Specific skill being evaluated (e.g., vocabulary, comprehension)';

COMMENT ON COLUMN lrg_session_skills.mastery_level IS 'Mastery level: beginner (0-49%), developing (50-74%), proficient (75-89%), advanced (90-100%)';
COMMENT ON COLUMN lrg_skill_mastery.mastery_pct IS 'Overall mastery percentage calculated from all historical attempts';


-- ============================================================
-- TABLE: lrg_xp_ledger
-- Stores all XP transactions for users
-- ============================================================

CREATE TABLE IF NOT EXISTS lrg_xp_ledger (
    xp_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    amount INTEGER NOT NULL CHECK (amount > 0),
    source TEXT NOT NULL CHECK (source IN (
        'session',
        'badge',
        'streak_bonus',
        'accuracy_bonus',
        'perfect_score_bonus',
        'speed_bonus',
        'first_session_bonus',
        'perfect_day_bonus',
        'daily_bonus',
        'level_up_bonus'
    )),
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Optional reference to session that generated this XP
    session_id UUID REFERENCES lrg_sessions(session_id) ON DELETE SET NULL
);

-- Indexes for faster XP lookups and aggregation
CREATE INDEX IF NOT EXISTS idx_xp_ledger_user_id ON lrg_xp_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_xp_ledger_occurred_at ON lrg_xp_ledger(occurred_at);
CREATE INDEX IF NOT EXISTS idx_xp_ledger_user_date ON lrg_xp_ledger(user_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_xp_ledger_source ON lrg_xp_ledger(source);


-- ============================================================
-- TABLE: lrg_streaks
-- Tracks user learning streaks
-- ============================================================

CREATE TABLE IF NOT EXISTS lrg_streaks (
    streak_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    current_streak INTEGER NOT NULL DEFAULT 0 CHECK (current_streak >= 0),
    longest_streak INTEGER NOT NULL DEFAULT 0 CHECK (longest_streak >= 0),
    last_active_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster user streak lookups
CREATE INDEX IF NOT EXISTS idx_streaks_user_id ON lrg_streaks(user_id);
CREATE INDEX IF NOT EXISTS idx_streaks_last_active ON lrg_streaks(last_active_date);


-- ============================================================
-- TABLE: lrg_daily_activity
-- Tracks daily user activity for streak and progress tracking
-- ============================================================

CREATE TABLE IF NOT EXISTS lrg_daily_activity (
    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    activity_date DATE NOT NULL,

    -- Session counts by modality
    listening_sessions INTEGER NOT NULL DEFAULT 0,
    reading_sessions INTEGER NOT NULL DEFAULT 0,
    grammar_sessions INTEGER NOT NULL DEFAULT 0,

    -- Completion flags
    listening_done BOOLEAN DEFAULT FALSE,
    reading_done BOOLEAN DEFAULT FALSE,
    grammar_done BOOLEAN DEFAULT FALSE,

    -- Daily metrics
    total_sessions INTEGER NOT NULL DEFAULT 0,
    total_xp_earned INTEGER NOT NULL DEFAULT 0,
    total_time_sec INTEGER NOT NULL DEFAULT 0,

    -- Streak day number (if part of active streak)
    streak_day INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_user_activity_date UNIQUE (user_id, activity_date)
);

-- Indexes for daily activity queries
CREATE INDEX IF NOT EXISTS idx_daily_activity_user_id ON lrg_daily_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_activity_date ON lrg_daily_activity(activity_date);
CREATE INDEX IF NOT EXISTS idx_daily_activity_user_date ON lrg_daily_activity(user_id, activity_date);


-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE lrg_xp_ledger IS 'Ledger of all XP transactions for gamification';
COMMENT ON TABLE lrg_streaks IS 'User learning streak tracking for daily engagement';
COMMENT ON TABLE lrg_daily_activity IS 'Daily user activity summary for progress tracking';

COMMENT ON COLUMN lrg_xp_ledger.source IS 'Source of XP: session, badge, various bonuses';
COMMENT ON COLUMN lrg_xp_ledger.amount IS 'XP amount awarded (must be positive)';
COMMENT ON COLUMN lrg_streaks.current_streak IS 'Current consecutive days with activity';
COMMENT ON COLUMN lrg_streaks.longest_streak IS 'Longest streak ever achieved by user';
COMMENT ON COLUMN lrg_daily_activity.streak_day IS 'Day number in streak sequence, NULL if streak broken';
