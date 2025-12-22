from src.extract import SpotifyAPI, MusicBrainzAPI, ReccoBeats, BillBoardChart
from datetime import date, timedelta
import re
import unicodedata
import time
import pandas as pd
import sqlalchemy as sa



def get_spotify_song_ids_and_artists(sp, chart) -> tuple[list, list, list, list]:
    """
    Returns:
        - chart: chart entries with song_id and artist_id (primary artist) added
        - song_ids: list of unique song IDs
        - artists: list of unique artist dicts
        - song_artists: list of (song_id, artist_id) tuples for all song-artist relationships
    """
    artists = []
    song_ids = []
    song_artists = []
    
    total = len(chart)
    print(f"  Searching Spotify for {total} songs...")
    
    for idx, song in enumerate(chart, 1):
        if idx % 10 == 0 or idx == 1:
            print(f"  Processing song {idx}/{total}: {song.get('title', 'Unknown')} by {song.get('artist', 'Unknown')}")
        artist = normalize_artist_name(song["artist"])
        res = sp.search_song(song["title"], artist)
        # add spotify ID and primary artist reference to each entry
        # initialize as null in case not found
        song["song_id"] = None
        song["artist_id"] = None

        # if the song is found, add song and artist
        if res and res != -1:
            track_id = res.get("id")
            track_artists = res.get("artists", [])

            if track_id:
                song_ids.append(track_id)
                song["song_id"] = track_id

            # store primary artist for the chart entry
            if track_artists:
                primary_artist = track_artists[0]
                song["artist_id"] = primary_artist.get("id")

            # maintain a de‑duplicated list of all artists we encounter
            # and track all song-artist relationships
            existing_ids = {a["id"] for a in artists}
            for item in track_artists:
                artist_id = item.get("id")
                artist_url = item.get("external_urls", {}).get("spotify")
                artist_name = item.get("name")
                
                if artist_id:
                    # Add to artists list if not seen before
                    if artist_id not in existing_ids:
                        artists.append(
                            {
                                "name": artist_name,
                                "id": artist_id,
                                "url": artist_url,
                            }
                        )
                        existing_ids.add(artist_id)
                    
                    # Track song-artist relationship
                    if track_id:
                        song_artists.append({
                            "song_id": track_id,
                            "artist_id": artist_id
                        })
        print(idx)
    return (chart, song_ids, artists, song_artists)


def normalize_artist_name(artist) -> str:
    #special case
    if artist == "JEONGYEON, JIHYO & CHAEYOUNG Of TWICE":
        artist = "TWICE"
    #only need to get one artist if there are multipl
    else:
        for c in ["Featuring", ",", "&", ":", "With"]:
            if c.lower() in artist.lower():
                artist = artist.split(c)[0]
    
    return artist
    

def get_tags_music_brainz(mb, artists):
    mbids = []
    for artist in artists:
        print(artist)

        url = artist['url']
        artist_id = artist.get('id')  # Spotify artist_id for database check
        mbid = mb.get_mbid(url, artist_id=artist_id)
        if mbid:
            artist['mbid'] = mbid
            tag = mb.mb_get_artist_tag(mbid, artist_id=artist_id)
            if tag:
                artist['tag'] = tag
        else:
            print(f"unable to get mbid for {url}")
        # time.sleep(1)


def get_audio_details(rec, song_ids):
    """
    Fetch audio features for songs from ReccoBeats API.
    Includes retry logic with exponential backoff for 429 rate limit errors.
    """
    if not song_ids:
        print("No song IDs provided, returning empty dataframe")
        return pd.DataFrame()
    
    total = len(song_ids)
    print(f"Fetching audio details for {total} songs...")
    
    BATCH_SIZE = 40
    all_results = []
    
    # Fetch song details in batches
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_num, i in enumerate(range(0, len(song_ids), BATCH_SIZE), 1):
        batch = song_ids[i : i + BATCH_SIZE]
        print(f"  Fetching batch {batch_num}/{num_batches} ({len(batch)} songs)...")
        results = rec.get_recco_song_details(batch)
        if results:
            # Extract song_id and artist_ids from each result
            for r in results:
                # Extract song_id from href (e.g., "https://api.reccobeats.com/v1/track/123" -> "123")
                song_id = None
                if 'href' in r:
                    song_id = r['href'].split('/')[-1]
                
                # Extract artist_ids from artists array
                # artist_ids = []
                # if 'artists' in r and isinstance(r['artists'], list):
                #     artist_ids = [
                #         artist['href'].split('/')[-1] 
                #         for artist in r['artists'] 
                #         if 'href' in artist
                #     ]
                
                # Add song_id and artist_ids to the result
                r['song_id'] = song_id
                # r['artist_ids'] = artist_ids
                all_results.append(r)
            
            print(f"  Retrieved {len(results)} song details")
        else:
            print(f"  No results for batch {batch_num}")
        
        # Rate limiting - increased sleep time between batches to avoid 429 errors
        if batch_num < num_batches:
            time.sleep(2)  # Increased from 1 to 2 seconds

    if not all_results:
        print("No audio details retrieved, returning empty dataframe")
        return pd.DataFrame()

    print(f"Fetching audio analysis for {len(all_results)} songs...")
    # Fetch audio analysis for each song with rate limiting
    for idx, item in enumerate(all_results, 1):
        if idx % 10 == 0:
            print(f"  Processing audio analysis {idx}/{len(all_results)}...")
        # Use the song_id we extracted, or fall back to 'id' field
        track_id = item.get('id')
        song_id = item.get('song_id')  # Spotify song_id for database check
        if track_id:
            res = rec.get_recco_audio_analysis(track_id, song_id=song_id)
            if res:
                item.update(res)
        
        # Rate limiting - sleep between individual requests to avoid 429 errors
        # Only sleep if not the last item
        if idx < len(all_results):
            time.sleep(0.5)  # 500ms delay between requests
    
    print(f"Completed fetching audio details for {len(all_results)} songs")

    audio_features = pd.DataFrame(all_results)
    if audio_features.empty:
        return pd.DataFrame()
    
    # song_id and artist_ids are already extracted and added above
    # Rename columns to snake_case to match database schema
    audio_features.rename(columns={'durationMs': 'duration_ms'}, inplace=True)
    
    # Drop unnecessary columns that shouldn't be in the songs table
    dropped = [
        "ean", 
        "availableCountries", 
        "isrc", 
        "upc", 
        "href",
        "artists",  # Artist info is in song_artists junction table
        "id",  # ReccoBeats ID - we use song_id (Spotify ID) instead
        "trackTitle",  # We have title from Billboard
        "artist_ids",  # This is an array, not suitable for songs table
    ]
    audio_features.drop(columns=dropped, inplace=True, errors="ignore")
    return audio_features



def most_recent_friday(ref_date=None):
    # Use today's date if none is provided
    if ref_date is None:
        ref_date = date.today()
    
    days_since_friday = (ref_date.weekday() - 4) % 7
    return ref_date - timedelta(days=days_since_friday)


def create_chart_object(chart):
    rows = []
    for entry in chart.entries:
        rows.append({
            "title": entry.title,
            "artist": entry.artist,
            "rank": entry.rank,
            "is_new": entry.isNew,
            "weeks": entry.weeks,
            "peak_pos": entry.peakPos
        })
    return rows


def get_dataframes(chart_week: str):
    print("getting dataframes")
    """
    Build dataframes that align with the schema:
    - chart_weeks (PK: chart_week)
    - chart_entries (PK: chart_week, rank)
    - songs (PK: song_id)
    - artists (PK: artist_id)
    - song_artists (PK: song_id, artist_id) - many-to-many relationship
    """


    sp = SpotifyAPI()
    mb = MusicBrainzAPI()
    rec = ReccoBeats()

    temp = BillBoardChart(chart_week).data
    chart = create_chart_object(temp)

    chart, song_ids, artists, song_artists = get_spotify_song_ids_and_artists(sp, chart)
    get_tags_music_brainz(mb, artists)

    df_audio = get_audio_details(rec, song_ids)
    df_artists = pd.DataFrame(artists)
    df_chart = pd.DataFrame(chart)

    # add chart_week and normalize id column names
    df_chart["chart_week"] = chart_week

    if not df_artists.empty:
        df_artists.rename(columns={"id": "artist_id"}, inplace=True)

    # songs table
    # one row per song with FKs into audio features and artists (primary artist)
    if not df_chart.empty and "song_id" in df_chart.columns and "title" in df_chart.columns:
        songs_with_ids = df_chart[df_chart["song_id"].notna()][["song_id", "title"]]
        if not songs_with_ids.empty:
            if df_audio is not None and not df_audio.empty:
                songs = (
                    songs_with_ids
                    .merge(df_audio, on="song_id", how="left")
                    .drop_duplicates(subset=["song_id"])
                    .reset_index(drop=True)
                )
            else:
                # If no audio features, just use the song_id and title
                songs = (
                    songs_with_ids
                    .drop_duplicates(subset=["song_id"])
                    .reset_index(drop=True)
                )
        else:
            # No songs found, create empty dataframe
            songs = pd.DataFrame(columns=["song_id", "title"])
            if df_audio is not None and not df_audio.empty:
                for col in df_audio.columns:
                    if col != "song_id":
                        songs[col] = None
    else:
        # Chart is empty
        songs = pd.DataFrame(columns=["song_id", "title"])
        if df_audio is not None and not df_audio.empty:
            for col in df_audio.columns:
                if col != "song_id":
                    songs[col] = None

    # artists table
    # one row per artist with FKs into songs and artists (primary artist)
    if not df_artists.empty:
        artists_df = (
            df_artists.drop_duplicates(subset=["artist_id"]).reset_index(drop=True)
        )
    else:
        artists_df = pd.DataFrame(columns=["artist_id", "name", "url", "mbid", "tag"])

    # song_artists table 
    # one row per (song_id, artist_id) for many-to-many relationship
    if song_artists:
        song_artists_df = (
            pd.DataFrame(song_artists)
            .drop_duplicates(subset=["song_id", "artist_id"])
            .reset_index(drop=True)
        )
    else:
        song_artists_df = pd.DataFrame(columns=["song_id", "artist_id"])


    # chart_weeks table
    # one row per chart week
    chart_weeks = pd.DataFrame({"chart_week": [chart_week]})


    # chart_entries table
    # one row per (chart_week, rank) with FKs into songs and artists (primary artist)
    required_cols = ["chart_week", "rank", "song_id", "artist_id", "is_new", "weeks", "peak_pos", "title", "artist"]
    for col in required_cols:
        if col not in df_chart.columns:
            df_chart[col] = None
    
    chart_entries = df_chart[required_cols].copy()

    return {
        "chart_weeks": chart_weeks,
        "chart_entries": chart_entries,
        "songs": songs,
        "artists": artists_df,
        "song_artists": song_artists_df,
    }
