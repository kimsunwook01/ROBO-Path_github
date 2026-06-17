-- Add terrain_tag column to nodes table, which was missing in initial schema
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS terrain_tag VARCHAR(50);
