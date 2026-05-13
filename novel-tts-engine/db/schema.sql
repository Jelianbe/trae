-- Novel-TTS-Engine Database Schema
-- Last updated: 2026-05-07
-- Note: PRAGMA foreign_keys = ON must be set in application code
-- Simplified for MVP: Removed sfx_words, progress tables and non-essential fields

CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    aliases TEXT NOT NULL DEFAULT '[]',
    gender TEXT DEFAULT 'unknown' CHECK(gender IN ('male', 'female', 'unknown')),
    first_appearance INTEGER,
    vector BLOB,
    is_locked INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, name)
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'splitting', 'analyzing', 'generating', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sentences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id INTEGER NOT NULL,
    sentence_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    sentence_type TEXT,
    speaker_id INTEGER,
    emotion TEXT,
    speed REAL DEFAULT 1.0,
    tone TEXT,
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    FOREIGN KEY (speaker_id) REFERENCES characters(id) ON DELETE SET NULL,
    UNIQUE(chapter_id, sentence_index)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sentences_chapter ON sentences(chapter_id);
CREATE INDEX IF NOT EXISTS idx_sentences_speaker ON sentences(speaker_id);
CREATE INDEX IF NOT EXISTS idx_sentences_chapter_index ON sentences(chapter_id, sentence_index);
CREATE INDEX IF NOT EXISTS idx_characters_gender ON characters(gender);
CREATE INDEX IF NOT EXISTS idx_characters_first_appearance ON characters(first_appearance);