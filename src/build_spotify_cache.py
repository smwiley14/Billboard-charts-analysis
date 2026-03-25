import time
import psycopg2
from extract import SpotifyAPI
from dotenv import load_dotenv
import os

load_dotenv()

# Connect to postgres
conn = psycopg2.connect(os.getenv("MUSIC_WAREHOUSE_DATABASE_URL"))
cur = conn.cursor()

# Get all unique title+artist combos not yet in cache
cur.execute("""
    SELECT DISTINCT c.title, c.artist 
    FROM charts c
    LEFT JOIN spotify_id_cache s ON c.title = s.title AND c.artist = s.artist
    WHERE s.spotify_id IS NULL
""")
songs = cur.fetchall()
total = len(songs)
print(f"Found {total} songs to look up")

sp = SpotifyAPI(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET")
)

for idx, (title, artist) in enumerate(songs, 1):
    print(f"[{idx}/{total}] {title} by {artist}")
    
    try:
        res = sp.search_song(title, artist)
        spotify_id = res['id'] if res and res != -1 else None
    except Exception as e:
        print(f"  Error: {e}")
        spotify_id = None
    
    cur.execute("""
        INSERT INTO spotify_id_cache (title, artist, spotify_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (title, artist) DO NOTHING
    """, (title, artist, spotify_id))
    conn.commit()
    
    time.sleep(2)  # 2 seconds between requests

cur.close()
conn.close()
print("Done!")