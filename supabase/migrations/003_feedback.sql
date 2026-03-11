-- User feedback on similarity results
-- Transparent: collected but does NOT influence similarity (yet)
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_song_id UUID REFERENCES songs(id),
    result_song_id UUID REFERENCES songs(id),
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
