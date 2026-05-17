-- Migration 024: Optional reason tags for negative feedback

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
