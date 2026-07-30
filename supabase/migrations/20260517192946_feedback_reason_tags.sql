-- Optional reason tags for negative feedback.
--
-- Recovered from the codex/beattrack-improvement-plan branch, where it was
-- numbered 024 and never merged. The column exists in the live database
-- already; this file is here so a rebuild from supabase/migrations/
-- reproduces it. Renamed to the timestamp convention using the original
-- authoring time. Nothing else references reason_tag, so the position in
-- the sequence is not load-bearing.

ALTER TABLE public.feedback
    ADD COLUMN IF NOT EXISTS reason_tag TEXT
    CHECK (
        reason_tag IS NULL
        OR reason_tag IN (
            'wrong_energy',
            'wrong_genre',
            'duplicate_version',
            'too_obvious',
            'bad_metadata',
            'other'
        )
    );

CREATE INDEX IF NOT EXISTS idx_feedback_reason_tag
    ON public.feedback (reason_tag)
    WHERE reason_tag IS NOT NULL;
