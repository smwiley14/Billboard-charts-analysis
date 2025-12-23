SELECT 'CREATE DATABASE music_warehouse'
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'music_warehouse'
)\gexec

\c music_warehouse

-- Music Chart Data Warehouse Schema
-- This DDL creates the tables for storing Billboard chart data with song and artist information

-- Drop tables if they exist (for clean setup - remove in production)
-- DROP TABLE IF EXISTS chart_entries CASCADE;
-- DROP TABLE IF EXISTS song_artists CASCADE;
-- DROP TABLE IF EXISTS chart_weeks CASCADE;
-- DROP TABLE IF EXISTS songs CASCADE;
-- DROP TABLE IF EXISTS artists CASCADE;

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

-- Chart Weeks: Represents each week for which chart data is collected
CREATE TABLE IF NOT EXISTS chart_weeks (
    chart_week DATE PRIMARY KEY
);

COMMENT ON TABLE chart_weeks IS 'Represents each week for which Billboard chart data is collected';
COMMENT ON COLUMN chart_weeks.chart_week IS 'The date of the chart week (typically a Friday)';

-- Artists: Unique artists appearing on charts
CREATE TABLE IF NOT EXISTS artists (
    artist_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    url TEXT,
    mbid VARCHAR(255),  -- MusicBrainz ID
    tag VARCHAR(255)    -- Primary genre/tag from MusicBrainz
);

COMMENT ON TABLE artists IS 'Unique artists that appear on Billboard charts';
COMMENT ON COLUMN artists.artist_id IS 'Spotify artist ID (primary key)';
COMMENT ON COLUMN artists.name IS 'Artist name';
COMMENT ON COLUMN artists.url IS 'Spotify URL for the artist';
COMMENT ON COLUMN artists.mbid IS 'MusicBrainz identifier';
COMMENT ON COLUMN artists.tag IS 'Primary genre/tag from MusicBrainz';

-- Songs: Unique songs appearing on charts
-- Note: Audio feature columns are dynamically added from ReccoBeats API
-- Common columns include: danceability, energy, valence, tempo, key, mode, etc.
CREATE TABLE IF NOT EXISTS songs (
    song_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    -- Additional audio feature columns will be added dynamically by pandas to_sql
    -- Common audio features from ReccoBeats/Spotify include:
    duration_ms INTEGER,        -- always an integer
    popularity SMALLINT,        -- 0–100

    acousticness REAL,          -- float 0.0–1.0
    danceability REAL,          -- float 0.0–1.0
    energy REAL,                -- float 0.0–1.0
    instrumentalness REAL,      -- float 0.0–1.0
    key SMALLINT,               -- -1 to 11
    liveness REAL,              -- float 0.0–1.0
    loudness REAL,              -- typically -60 to 0 dB
    mode SMALLINT,              -- 0 or 1
    speechiness REAL,           -- float 0.0–1.0
    tempo REAL,                 -- 0–250 BPM
    valence REAL                -- float 0.0–1.0
    -- time_signature INTEGER
);

COMMENT ON TABLE songs IS 'Unique songs that appear on Billboard charts';
COMMENT ON COLUMN songs.song_id IS 'Spotify track ID (primary key)';
COMMENT ON COLUMN songs.title IS 'Song title';

-- ============================================================================
-- JUNCTION TABLE
-- ============================================================================

-- Song Artists: Many-to-many relationship between songs and artists
-- A song can have multiple artists (collaborations, features, etc.)
CREATE TABLE IF NOT EXISTS song_artists (
    song_id VARCHAR(255) NOT NULL,
    artist_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (song_id, artist_id),
    CONSTRAINT fk_song_artists_song FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE,
    CONSTRAINT fk_song_artists_artist FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE
);

CREATE INDEX idx_song_artists_song_id ON song_artists(song_id);
CREATE INDEX idx_song_artists_artist_id ON song_artists(artist_id);

COMMENT ON TABLE song_artists IS 'Junction table linking songs to all their associated artists (many-to-many)';
COMMENT ON COLUMN song_artists.song_id IS 'Foreign key to songs table';
COMMENT ON COLUMN song_artists.artist_id IS 'Foreign key to artists table';

-- ============================================================================
-- FACT TABLE
-- ============================================================================

-- Chart Entries: Individual chart positions for each week
CREATE TABLE IF NOT EXISTS chart_entries (
    chart_week DATE NOT NULL,
    rank INTEGER NOT NULL,
    song_id VARCHAR(255),
    artist_id VARCHAR(255),  -- Primary artist for this chart entry
    is_new BOOLEAN,
    weeks INTEGER,           -- Number of weeks on chart
    peak_pos INTEGER,         -- Peak position achieved
    title VARCHAR(500),      -- Denormalized for convenience
    artist VARCHAR(500),    -- Denormalized for convenience (original Billboard artist string)
    PRIMARY KEY (chart_week, rank),
    CONSTRAINT fk_chart_entries_week FOREIGN KEY (chart_week) REFERENCES chart_weeks(chart_week) ON DELETE CASCADE,
    CONSTRAINT fk_chart_entries_song FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE SET NULL,
    CONSTRAINT fk_chart_entries_artist FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE SET NULL,
    CONSTRAINT chk_rank_range CHECK (rank >= 1 AND rank <= 100)
);

CREATE INDEX idx_chart_entries_chart_week ON chart_entries(chart_week);
CREATE INDEX idx_chart_entries_song_id ON chart_entries(song_id);
CREATE INDEX idx_chart_entries_artist_id ON chart_entries(artist_id);
CREATE INDEX idx_chart_entries_rank ON chart_entries(rank);

COMMENT ON TABLE chart_entries IS 'Individual chart positions for each week (fact table)';
COMMENT ON COLUMN chart_entries.chart_week IS 'Foreign key to chart_weeks table';
COMMENT ON COLUMN chart_entries.rank IS 'Chart position (1-100)';
COMMENT ON COLUMN chart_entries.song_id IS 'Foreign key to songs table (may be NULL if song not found in Spotify)';
COMMENT ON COLUMN chart_entries.artist_id IS 'Foreign key to artists table (primary artist, may be NULL)';
COMMENT ON COLUMN chart_entries.is_new IS 'Whether this entry is new to the chart this week';
COMMENT ON COLUMN chart_entries.weeks IS 'Number of consecutive weeks this song has been on the chart';
COMMENT ON COLUMN chart_entries.peak_pos IS 'Highest position this song has achieved';
COMMENT ON COLUMN chart_entries.title IS 'Song title (denormalized from Billboard)';
COMMENT ON COLUMN chart_entries.artist IS 'Artist name as it appears on Billboard (denormalized)';

-- ============================================================================
-- USEFUL VIEWS (Optional)
-- ============================================================================

-- View: Chart entries with full song and artist details
CREATE OR REPLACE VIEW chart_entries_detailed AS
SELECT 
    ce.chart_week,
    ce.rank,
    ce.is_new,
    ce.weeks,
    ce.peak_pos,
    s.song_id,
    s.title AS song_title,
    a.artist_id,
    a.name AS artist_name,
    a.tag AS artist_genre,
    ce.title AS billboard_title,  -- Original Billboard title
    ce.artist AS billboard_artist  -- Original Billboard artist string
FROM chart_entries ce
LEFT JOIN songs s ON ce.song_id = s.song_id
LEFT JOIN artists a ON ce.artist_id = a.artist_id;

COMMENT ON VIEW chart_entries_detailed IS 'Chart entries with joined song and artist details';

-- View: Songs with all their artists
CREATE OR REPLACE VIEW songs_with_artists AS
SELECT 
    s.song_id,
    s.title,
    STRING_AGG(a.name, ', ' ORDER BY a.name) AS all_artists,
    ARRAY_AGG(a.artist_id ORDER BY a.name) AS artist_ids
FROM songs s
LEFT JOIN song_artists sa ON s.song_id = sa.song_id
LEFT JOIN artists a ON sa.artist_id = a.artist_id
GROUP BY s.song_id, s.title;

COMMENT ON VIEW songs_with_artists IS 'Songs with all associated artists aggregated';

