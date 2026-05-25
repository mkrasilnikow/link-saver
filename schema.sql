-- Run this in Supabase SQL Editor to set up the database

CREATE TABLE links (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url         TEXT NOT NULL,
  title       TEXT,
  description TEXT,
  thumbnail   TEXT,
  type        TEXT,
  tags        TEXT[],
  status      TEXT DEFAULT 'unread',
  source      TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Full-text search index (Russian + English)
ALTER TABLE links ADD COLUMN fts tsvector
  GENERATED ALWAYS AS (
    to_tsvector('russian', coalesce(title, '') || ' ' || coalesce(description, ''))
  ) STORED;

CREATE INDEX links_fts_idx ON links USING gin(fts);
CREATE INDEX links_tags_idx ON links USING gin(tags);
CREATE INDEX links_status_idx ON links(status);
CREATE INDEX links_created_idx ON links(created_at DESC);
