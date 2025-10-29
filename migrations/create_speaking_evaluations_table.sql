-- Migration: Create speaking_evaluations table
-- Description: Stores LLM-based speaking performance evaluations from session conversations
-- Author: System
-- Date: 2025-01-15

-- Create speaking_evaluations table
CREATE TABLE IF NOT EXISTS speaking_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_id UUID NOT NULL,
    language VARCHAR(50) NOT NULL,
    user_level VARCHAR(50) NOT NULL,
    total_turns INTEGER NOT NULL,
    scores JSONB NOT NULL,
    strengths JSONB NOT NULL,
    improvements JSONB NOT NULL,
    suggestions JSONB NOT NULL,
    conversation_summary TEXT NOT NULL,
    overall_score INTEGER NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    feedback_summary TEXT NOT NULL,
    fluency_level VARCHAR(50) NOT NULL,
    vocabulary_range VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add foreign key constraint (if sessions table exists)
-- Note: Uncomment if you want strict referential integrity
-- ALTER TABLE speaking_evaluations
--     ADD CONSTRAINT fk_speaking_evaluations_session
--     FOREIGN KEY (session_id)
--     REFERENCES sessions(id)
--     ON DELETE CASCADE;

-- Create indexes for common queries
CREATE INDEX idx_speaking_evaluations_user_id
    ON speaking_evaluations(user_id);

CREATE INDEX idx_speaking_evaluations_session_id
    ON speaking_evaluations(session_id);

CREATE INDEX idx_speaking_evaluations_created_at
    ON speaking_evaluations(created_at DESC);

CREATE INDEX idx_speaking_evaluations_overall_score
    ON speaking_evaluations(overall_score);

CREATE INDEX idx_speaking_evaluations_user_created
    ON speaking_evaluations(user_id, created_at DESC);

-- Create updated_at trigger function (if it doesn't exist)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_speaking_evaluations_updated_at
    BEFORE UPDATE ON speaking_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE speaking_evaluations IS 'Stores LLM-based speaking performance evaluations from session conversations';
COMMENT ON COLUMN speaking_evaluations.id IS 'Unique identifier for the evaluation';
COMMENT ON COLUMN speaking_evaluations.user_id IS 'ID of the user being evaluated';
COMMENT ON COLUMN speaking_evaluations.session_id IS 'ID of the session being evaluated';
COMMENT ON COLUMN speaking_evaluations.language IS 'Target language being evaluated';
COMMENT ON COLUMN speaking_evaluations.user_level IS 'Proficiency level of the user (beginner, intermediate, advanced)';
COMMENT ON COLUMN speaking_evaluations.total_turns IS 'Number of user speaking turns in the conversation';
COMMENT ON COLUMN speaking_evaluations.scores IS 'JSON object containing detailed scores for fluency, pronunciation, vocabulary, grammar, coherence, comprehension';
COMMENT ON COLUMN speaking_evaluations.strengths IS 'JSON array of identified strengths';
COMMENT ON COLUMN speaking_evaluations.improvements IS 'JSON array of areas for improvement';
COMMENT ON COLUMN speaking_evaluations.suggestions IS 'JSON array of specific suggestions for improvement';
COMMENT ON COLUMN speaking_evaluations.conversation_summary IS 'Brief summary of what the conversation was about';
COMMENT ON COLUMN speaking_evaluations.overall_score IS 'Overall speaking score (0-100)';
COMMENT ON COLUMN speaking_evaluations.feedback_summary IS 'Summary feedback and encouragement';
COMMENT ON COLUMN speaking_evaluations.fluency_level IS 'Assessed fluency level (beginner, elementary, intermediate, upper-intermediate, advanced)';
COMMENT ON COLUMN speaking_evaluations.vocabulary_range IS 'Assessed vocabulary range (limited, basic, moderate, good, extensive)';
COMMENT ON COLUMN speaking_evaluations.created_at IS 'Timestamp when evaluation was created';
COMMENT ON COLUMN speaking_evaluations.updated_at IS 'Timestamp when evaluation was last updated';

-- Grant permissions (adjust as needed for your security model)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON speaking_evaluations TO your_app_user;

-- Sample query to verify table creation
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'speaking_evaluations'
-- ORDER BY ordinal_position;
