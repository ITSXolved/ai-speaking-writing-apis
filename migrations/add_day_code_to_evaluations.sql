-- Migration: Add day_code to evaluation tables
-- This allows tracking which day's content was evaluated

-- Add day_code to speaking_evaluations
ALTER TABLE public.speaking_evaluations
ADD COLUMN IF NOT EXISTS day_code text;

-- Add foreign key constraint
ALTER TABLE public.speaking_evaluations
ADD CONSTRAINT IF NOT EXISTS speaking_evaluations_day_code_fkey
  FOREIGN KEY (day_code) REFERENCES public.study_days(day_code);

-- Add day_code to writing_evaluations
ALTER TABLE public.writing_evaluations
ADD COLUMN IF NOT EXISTS day_code text;

-- Add foreign key constraint
ALTER TABLE public.writing_evaluations
ADD CONSTRAINT IF NOT EXISTS writing_evaluations_day_code_fkey
  FOREIGN KEY (day_code) REFERENCES public.study_days(day_code);

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_speaking_evaluations_day_code
  ON public.speaking_evaluations(day_code);

CREATE INDEX IF NOT EXISTS idx_speaking_evaluations_user_day
  ON public.speaking_evaluations(user_id, day_code);

CREATE INDEX IF NOT EXISTS idx_writing_evaluations_day_code
  ON public.writing_evaluations(day_code);

CREATE INDEX IF NOT EXISTS idx_writing_evaluations_user_day
  ON public.writing_evaluations(user_id, day_code);

-- Comments
COMMENT ON COLUMN public.speaking_evaluations.day_code IS 'Day code (e.g., day1, day2) to track which day content was evaluated';
COMMENT ON COLUMN public.writing_evaluations.day_code IS 'Day code (e.g., day1, day2) to track which day content was evaluated';
