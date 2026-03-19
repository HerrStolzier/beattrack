-- Migration 021: RPC to update genre for existing songs (bypasses RLS)
-- Used by backfill_genre.py to batch-update genre from Deezer Album API.

CREATE OR REPLACE FUNCTION update_song_genre(song_id UUID, new_genre TEXT)
RETURNS VOID
LANGUAGE sql
SECURITY DEFINER
AS $$
    UPDATE songs SET genre = new_genre WHERE id = song_id;
$$;

-- Also add a batch variant for efficiency
CREATE OR REPLACE FUNCTION batch_update_genres(updates JSONB)
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    item JSONB;
    updated INT := 0;
BEGIN
    FOR item IN SELECT * FROM jsonb_array_elements(updates)
    LOOP
        UPDATE songs
        SET genre = item->>'genre'
        WHERE id = (item->>'id')::UUID;
        updated := updated + 1;
    END LOOP;
    RETURN updated;
END;
$$;
