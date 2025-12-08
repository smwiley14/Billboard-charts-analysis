-- Migration script to add missing columns to songs table
-- Run this if your songs table already exists but is missing audio feature columns

-- Add audio feature columns if they don't exist
DO $$ 
BEGIN
    -- Add columns one by one, only if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='popularity') THEN
        ALTER TABLE songs ADD COLUMN popularity DECIMAL(5,2);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='danceability') THEN
        ALTER TABLE songs ADD COLUMN danceability DECIMAL(5,4);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='energy') THEN
        ALTER TABLE songs ADD COLUMN energy DECIMAL(5,4);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='key') THEN
        ALTER TABLE songs ADD COLUMN key INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='loudness') THEN
        ALTER TABLE songs ADD COLUMN loudness DECIMAL(6,3);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='mode') THEN
        ALTER TABLE songs ADD COLUMN mode INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='speechiness') THEN
        ALTER TABLE songs ADD COLUMN speechiness DECIMAL(5,4);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='acousticness') THEN
        ALTER TABLE songs ADD COLUMN acousticness DECIMAL(5,4);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='instrumentalness') THEN
        ALTER TABLE songs ADD COLUMN instrumentalness DECIMAL(10,8);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='liveness') THEN
        ALTER TABLE songs ADD COLUMN liveness DECIMAL(5,4);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='valence') THEN
        ALTER TABLE songs ADD COLUMN valence DECIMAL(5,4);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='tempo') THEN
        ALTER TABLE songs ADD COLUMN tempo DECIMAL(6,3);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='duration_ms') THEN
        ALTER TABLE songs ADD COLUMN duration_ms INTEGER;
    END IF;
END $$;

