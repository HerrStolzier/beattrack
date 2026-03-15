-- Add genre and release_year columns for scope filtering
ALTER TABLE public.songs ADD COLUMN IF NOT EXISTS genre TEXT;
ALTER TABLE public.songs ADD COLUMN IF NOT EXISTS release_year INT;

-- Index for genre filtering
CREATE INDEX IF NOT EXISTS idx_songs_genre ON public.songs (genre);
